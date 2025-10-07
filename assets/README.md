# Branded Assets

This directory contains branded intro and outro videos for the YouTube uploads.

## Files

- `intro.mp4` - Branded intro video (should be short, 2-5 seconds)
- `outro.mp4` - Branded outro video (should be short, 2-5 seconds)

## Usage

These videos are automatically concatenated with downloaded Instagram videos
during the transformation process to create branded YouTube Shorts.

## Requirements

- **Format**: MP4
- **Duration**: 2-5 seconds each (keep short to maintain content focus)
- **Aspect Ratio**: Any (will be resized to fit 9:16 format)
- **Size**: Keep files small (< 5MB each)
- **Quality**: 1080p or lower for faster processing

## Creating Branded Assets

To create your own branded intro/outro videos:

1. **Design**: Create simple, branded content
   - Intro: Channel name, logo, tagline
   - Outro: Subscribe prompt, channel branding

2. **Duration**: Keep very short (2-5 seconds)
   - Longer intros/outros reduce main content time
   - Users prefer content-focused videos

3. **Style**: Match your channel branding
   - Consistent colors, fonts, graphics
   - Professional but not overwhelming

4. **Export Settings**:
   - Format: MP4
   - Codec: H.264
   - Resolution: 1080p or lower
   - Frame rate: 30fps or 60fps

## Configuration

The paths to these files are configured in the environment variables:

- `BRANDED_INTRO` (default: `./assets/intro.mp4`)
- `BRANDED_OUTRO` (default: `./assets/outro.mp4`)

## Demo Mode

In demo mode, the system will work without these files, but they enhance
the final output when available.

## Best Practices

1. **Keep it simple**: Simple branding is more effective
2. **Match content**: Ensure branding fits your content style
3. **Test duration**: Preview final videos to ensure good pacing
4. **Optimize size**: Compress files for faster processing
5. **Update regularly**: Refresh branding periodically

## Legal Considerations

Ensure your branded assets:
- Use original graphics or properly licensed content
- Comply with platform guidelines
- Don't infringe on others' trademarks
- Include proper attribution for any third-party content
