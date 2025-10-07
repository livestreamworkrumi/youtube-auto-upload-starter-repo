"""
Telegram bot for admin approval workflow and system control.

This module handles:
- Admin commands for system control
- Approval workflow for video uploads
- Status notifications and error alerts
- Target account management
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, Message
)

from .config import get_settings
from .db import get_db_session, update_system_status
from .models import (
    Approval, InstagramTarget, StatusEnum, Transform, Upload
)
from .utils import generate_seo_description, generate_seo_title

logger = logging.getLogger(__name__)


class AddTargetStates(StatesGroup):
    """States for adding Instagram target."""
    waiting_for_username = State()


class TelegramBot:
    """Telegram bot for admin control and approval workflow."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bot = None
        self.dp = None
        self.router = Router()
        
        # Admin ID validation
        self.admin_id = self.settings.telegram_admin_id
        
        # Setup handlers
        self._setup_handlers()
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.settings.is_demo_mode()
    
    def _setup_handlers(self):
        """Setup bot command and callback handlers."""
        
        # Start command
        @self.router.message(CommandStart())
        async def start_command(message: Message):
            if not self._is_admin(message.from_user.id):
                await message.reply("❌ Access denied. You are not authorized to use this bot.")
                return
            
            await message.reply(
                "🤖 YouTube Auto Upload Bot\n\n"
                "Available commands:\n"
                "/start - Start the scheduler\n"
                "/stop - Stop the scheduler\n"
                "/status - Show system status\n"
                "/add_target - Add Instagram target\n"
                "/remove_target - Remove Instagram target\n"
                "/list_targets - List all targets\n"
                "/help - Show help"
            )
        
        # Help command
        @self.router.message(Command("help"))
        async def help_command(message: Message):
            if not self._is_admin(message.from_user.id):
                await message.reply("❌ Access denied.")
                return
            
            help_text = """
🤖 YouTube Auto Upload Bot Help

📋 Commands:
/start - Start the video processing scheduler
/stop - Stop the video processing scheduler
/status - Show current system status and queue info
/add_target <username> - Add Instagram username to monitor
/remove_target <username> - Remove Instagram username
/list_targets - List all monitored Instagram accounts
/help - Show this help message

🔧 Approval Workflow:
When videos are ready for upload, you'll receive preview messages with:
• Video thumbnail
• Suggested title and description
• Original Instagram link
• Permission proof path
• Approve/Reject buttons

⚠️ Note: Only approved videos will be uploaded to YouTube.
            """
            await message.reply(help_text)
        
        # Start scheduler command
        @self.router.message(Command("start"))
        async def start_scheduler(message: Message):
            if not self._is_admin(message.from_user.id):
                await message.reply("❌ Access denied.")
                return
            
            try:
                update_system_status(scheduler_running=True)
                await message.reply("✅ Scheduler started successfully!")
            except Exception as e:
                await message.reply(f"❌ Failed to start scheduler: {e}")
        
        # Stop scheduler command
        @self.router.message(Command("stop"))
        async def stop_scheduler(message: Message):
            if not self._is_admin(message.from_user.id):
                await message.reply("❌ Access denied.")
                return
            
            try:
                update_system_status(scheduler_running=False)
                await message.reply("⏹️ Scheduler stopped successfully!")
            except Exception as e:
                await message.reply(f"❌ Failed to stop scheduler: {e}")
        
        # Status command
        @self.router.message(Command("status"))
        async def status_command(message: Message):
            if not self._is_admin(message.from_user.id):
                await message.reply("❌ Access denied.")
                return
            
            try:
                status_text = await self._get_status_text()
                await message.reply(status_text)
            except Exception as e:
                await message.reply(f"❌ Failed to get status: {e}")
        
        # Add target command
        @self.router.message(Command("add_target"))
        async def add_target_command(message: Message):
            if not self._is_admin(message.from_user.id):
                await message.reply("❌ Access denied.")
                return
            
            try:
                # Extract username from command
                parts = message.text.split()
                if len(parts) < 2:
                    await message.reply("❌ Please provide a username: /add_target <username>")
                    return
                
                username = parts[1].replace('@', '')
                await self._add_target(username, message)
            except Exception as e:
                await message.reply(f"❌ Failed to add target: {e}")
        
        # Remove target command
        @self.router.message(Command("remove_target"))
        async def remove_target_command(message: Message):
            if not self._is_admin(message.from_user.id):
                await message.reply("❌ Access denied.")
                return
            
            try:
                parts = message.text.split()
                if len(parts) < 2:
                    await message.reply("❌ Please provide a username: /remove_target <username>")
                    return
                
                username = parts[1].replace('@', '')
                await self._remove_target(username, message)
            except Exception as e:
                await message.reply(f"❌ Failed to remove target: {e}")
        
        # List targets command
        @self.router.message(Command("list_targets"))
        async def list_targets_command(message: Message):
            if not self._is_admin(message.from_user.id):
                await message.reply("❌ Access denied.")
                return
            
            try:
                targets_text = await self._get_targets_text()
                await message.reply(targets_text)
            except Exception as e:
                await message.reply(f"❌ Failed to list targets: {e}")
        
        # Approval callback handlers
        @self.router.callback_query(F.data.startswith("approve_"))
        async def approve_callback(callback: CallbackQuery):
            if not self._is_admin(callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            try:
                upload_id = int(callback.data.split("_")[1])
                await self._handle_approval(upload_id, True, callback)
            except Exception as e:
                await callback.answer(f"❌ Approval failed: {e}", show_alert=True)
        
        @self.router.callback_query(F.data.startswith("reject_"))
        async def reject_callback(callback: CallbackQuery):
            if not self._is_admin(callback.from_user.id):
                await callback.answer("❌ Access denied.", show_alert=True)
                return
            
            try:
                upload_id = int(callback.data.split("_")[1])
                await self._handle_approval(upload_id, False, callback)
            except Exception as e:
                await callback.answer(f"❌ Rejection failed: {e}", show_alert=True)
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is authorized admin."""
        return user_id == self.admin_id or self.is_demo_mode()
    
    async def _get_status_text(self) -> str:
        """Generate system status text."""
        with get_db_session() as session:
            # Get system status
            from .db import get_system_status
            system_status = get_system_status()
            
            # Get counts
            total_targets = session.query(InstagramTarget).filter_by(is_active=True).count()
            total_downloads = session.query(Transform).count()
            pending_approvals = session.query(Approval).filter_by(status=StatusEnum.PENDING).count()
            completed_uploads = session.query(Upload).filter_by(status=StatusEnum.COMPLETED).count()
            
            status_text = f"""
📊 System Status

🔄 Scheduler: {'Running' if system_status.get('scheduler_running') else 'Stopped'}
📅 Last Run: {system_status.get('last_run', 'Never')}
⏰ Next Run: {system_status.get('next_run', 'Not scheduled')}

📈 Statistics:
• Active Targets: {total_targets}
• Total Downloads: {total_downloads}
• Pending Approvals: {pending_approvals}
• Completed Uploads: {completed_uploads}

🎬 Mode: {'Demo' if self.is_demo_mode() else 'Production'}
            """
            
            return status_text.strip()
    
    async def _get_targets_text(self) -> str:
        """Generate targets list text."""
        with get_db_session() as session:
            targets = session.query(InstagramTarget).all()
            
            if not targets:
                return "📋 No Instagram targets configured."
            
            targets_text = "📋 Instagram Targets:\n\n"
            for target in targets:
                status = "✅ Active" if target.is_active else "❌ Inactive"
                last_checked = target.last_checked.strftime("%Y-%m-%d %H:%M") if target.last_checked else "Never"
                targets_text += f"• @{target.username} {status}\n  Last checked: {last_checked}\n\n"
            
            return targets_text.strip()
    
    async def _add_target(self, username: str, message: Message):
        """Add Instagram target."""
        with get_db_session() as session:
            # Check if target already exists
            existing = session.query(InstagramTarget).filter_by(username=username).first()
            if existing:
                await message.reply(f"⚠️ Target @{username} already exists.")
                return
            
            # Create new target
            target = InstagramTarget(username=username, is_active=True)
            session.add(target)
            session.commit()
            
            await message.reply(f"✅ Added target @{username} successfully!")
    
    async def _remove_target(self, username: str, message: Message):
        """Remove Instagram target."""
        with get_db_session() as session:
            target = session.query(InstagramTarget).filter_by(username=username).first()
            if not target:
                await message.reply(f"⚠️ Target @{username} not found.")
                return
            
            target.is_active = False
            session.commit()
            
            await message.reply(f"✅ Deactivated target @{username} successfully!")
    
    async def _handle_approval(self, upload_id: int, approved: bool, callback: CallbackQuery):
        """Handle upload approval or rejection."""
        with get_db_session() as session:
            upload = session.query(Upload).filter_by(id=upload_id).first()
            if not upload:
                await callback.answer("❌ Upload not found.", show_alert=True)
                return
            
            # Update approval record
            approval = session.query(Approval).filter_by(upload_id=upload_id).first()
            if approval:
                approval.status = StatusEnum.COMPLETED if approved else StatusEnum.REJECTED
                approval.approved_by = str(callback.from_user.id)
                approval.approved_at = datetime.utcnow()
                session.commit()
            
            # Update upload status
            upload.status = StatusEnum.COMPLETED if approved else StatusEnum.REJECTED
            session.commit()
            
            if approved:
                # Start upload process (this would be handled by workers)
                await callback.answer("✅ Upload approved! Processing...", show_alert=True)
                await callback.message.edit_text(
                    callback.message.text + "\n\n✅ **APPROVED** by admin",
                    parse_mode="Markdown"
                )
            else:
                await callback.answer("❌ Upload rejected.", show_alert=True)
                await callback.message.edit_text(
                    callback.message.text + "\n\n❌ **REJECTED** by admin",
                    parse_mode="Markdown"
                )
    
    async def send_upload_preview(self, upload: Upload, transform: Transform) -> bool:
        """Send upload preview for admin approval."""
        if self.is_demo_mode():
            logger.info(f"Demo mode: simulating preview send for upload {upload.id}")
            return True
        
        try:
            # Generate preview message
            preview_text = await self._generate_preview_text(upload, transform)
            
            # Create approval buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{upload.id}"),
                    InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{upload.id}")
                ]
            ])
            
            # Send thumbnail if available
            if transform.thumbnail_path and Path(transform.thumbnail_path).exists():
                photo = InputFile(transform.thumbnail_path)
                message = await self.bot.send_photo(
                    chat_id=self.admin_id,
                    photo=photo,
                    caption=preview_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                message = await self.bot.send_message(
                    chat_id=self.admin_id,
                    text=preview_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            
            # Store message ID for approval tracking
            with get_db_session() as session:
                approval = session.query(Approval).filter_by(upload_id=upload.id).first()
                if approval:
                    approval.telegram_message_id = message.message_id
                    session.commit()
            
            logger.info(f"Upload preview sent for upload {upload.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send upload preview: {e}")
            return False
    
    async def _generate_preview_text(self, upload: Upload, transform: Transform) -> str:
        """Generate preview text for upload."""
        download = transform.download
        
        preview_text = f"""
🎬 **Upload Preview**

📝 **Title:** {upload.title}

📋 **Description:**
{upload.description[:200]}{'...' if len(upload.description) > 200 else ''}

🏷️ **Tags:** {json.loads(upload.tags) if upload.tags else []}

👤 **Creator:** @{download.target.username}

🔗 **Original Post:** {download.source_url}

📄 **Permission Proof:** {download.permission_proof_path}

📊 **Video Info:**
• Duration: {transform.transform_duration_seconds}s
• Size: {download.file_size} bytes
• pHash: {transform.phash[:16]}...

⏰ **Ready for Upload:** {upload.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Please review and approve or reject this upload.
        """
        
        return preview_text.strip()
    
    async def send_error_notification(self, error_message: str, context: str = "") -> bool:
        """Send error notification to admin."""
        if self.is_demo_mode():
            logger.info(f"Demo mode: simulating error notification: {error_message}")
            return True
        
        try:
            error_text = f"""
🚨 **System Error**

❌ **Error:** {error_message}

📍 **Context:** {context}

⏰ **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

Please check the system logs for more details.
            """
            
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=error_text,
                parse_mode="Markdown"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            return False
    
    async def send_upload_success_notification(self, upload: Upload) -> bool:
        """Send upload success notification."""
        if self.is_demo_mode():
            logger.info(f"Demo mode: simulating upload success notification for {upload.yt_video_id}")
            return True
        
        try:
            success_text = f"""
✅ **Upload Successful**

🎬 **Video:** {upload.title}

🔗 **YouTube ID:** {upload.yt_video_id}

⏰ **Uploaded:** {upload.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}

The video has been uploaded successfully to YouTube!
            """
            
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=success_text,
                parse_mode="Markdown"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send success notification: {e}")
            return False
    
    async def start_bot(self):
        """Start the Telegram bot."""
        if self.is_demo_mode():
            logger.info("Demo mode: Telegram bot not started")
            return
        
        if not self.settings.telegram_bot_token:
            logger.error("Telegram bot token not configured")
            return
        
        try:
            self.bot = Bot(token=self.settings.telegram_bot_token)
            self.dp = Dispatcher()
            self.dp.include_router(self.router)
            
            logger.info("Telegram bot started successfully")
            
            # Start polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
    
    async def stop_bot(self):
        """Stop the Telegram bot."""
        if self.bot and self.dp:
            await self.dp.stop_polling()
            await self.bot.session.close()
            logger.info("Telegram bot stopped")


def create_telegram_bot() -> TelegramBot:
    """Create and return a Telegram bot instance."""
    return TelegramBot()


if __name__ == "__main__":
    # Allow running this module directly for testing
    import asyncio
    
    async def test_bot():
        bot = create_telegram_bot()
        if not bot.is_demo_mode():
            await bot.start_bot()
        else:
            print("Demo mode: Telegram bot test completed")
    
    asyncio.run(test_bot())
