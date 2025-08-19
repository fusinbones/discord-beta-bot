# Jim - Beta Testing Assistant

Enhanced functionality for your existing Discord bot "Jim" to assist beta testing teams with tracking progress, managing bug reports, and coordinating testing efforts using Google Gemini AI.

## Overview

This upgrade transforms Jim into a comprehensive beta testing coordinator while maintaining his existing functionality. Jim will now be able to:

### 🔍 **Message Tracking**
- Automatically tracks ALL messages in designated beta testing channels
- Stores conversation history for context and analysis
- Provides searchable message database

### 🐛 **Bug Reporting System**
- `!bug <description>` - Report bugs with automatic staff notification
- Detailed bug reports with timestamps, user info, and unique IDs
- Bug status tracking (open/fixed)
- Staff role tagging for immediate attention

### 📋 **Testing Coordination**
- `!whatsnew` - Private message latest updates to beta testers only
- `!status` - View current testing progress and bug statistics
- `!help-test <question>` - AI-powered assistance for testing questions
- Feature progress tracking with status updates

### 🤖 **AI Integration**
- Google Gemini AI provides intelligent responses
- Context-aware assistance based on current testing state
- Helps testers understand what to test and current priorities

### 👥 **Role-Based Access**
- Beta tester role verification for sensitive commands
- Admin-only commands for managing updates and bug status
- Staff role tagging for bug notifications

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- Discord Developer Account
- Google AI Studio Account (for Gemini API)

### 2. Discord Bot Setup
**Since you already have Jim set up, you'll just need to:**
1. Ensure Jim has the necessary permissions in your beta testing channels:
   - Send Messages
   - Read Message History
   - Embed Links
   - Mention Everyone
   - Use Slash Commands
2. Use Jim's existing bot token in the configuration

### 3. Google Gemini Setup
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key for configuration

### 4. Installation
```bash
# Clone or download the project
cd discord-beta-bot

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### 5. Configuration

#### Environment Variables (.env)
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

#### Bot Configuration (config.json)
```json
{
  "beta_channels": ["CHANNEL_ID_1", "CHANNEL_ID_2"],
  "staff_role_name": "staff",
  "beta_tester_role_name": "beta tester",
  "guild_id": "YOUR_GUILD_ID"
}
```

**To get Channel IDs:**
1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on channels and select "Copy ID"
3. Add these IDs to the `beta_channels` array

### 6. Running the Bot
```bash
python bot.py
```

## Commands

### For Beta Testers
- `!bug <description>` - Report a bug (automatically notifies staff)
- `!whatsnew` - Get latest updates via DM (beta testers only)
- `!status` - View current testing progress and statistics
- `!help-test <question>` - Get AI assistance for testing questions

### For Administrators
- `!add-update <content>` - Add new update for beta testers
- `!close-bug <bug_id>` - Mark a bug as fixed
- `!update-feature <name> <status> [notes]` - Update feature testing status

## Database Schema

The bot uses SQLite to store:
- **Messages**: All beta channel conversations
- **Bugs**: Bug reports with status tracking
- **Testing Progress**: Feature status and notes
- **Updates**: What's new content for testers

## Example Usage

### Reporting a Bug
```
!bug whenever I open the stock photo creator, it keeps crashing the app
```
This will:
- Create a detailed bug report
- Assign a unique bug ID
- Tag @staff role
- Store in database for tracking

### Getting Updates
```
!whatsnew
```
This will:
- Verify beta tester role
- Send latest 5 updates via DM
- Include timestamps and who added each update

### AI Assistance
```
!help-test what should I focus on testing today?
```
The AI will analyze:
- Current open bugs
- Feature testing progress
- Recent conversations
- Provide targeted testing suggestions

## Customization

### Adding New Commands
Add new commands by creating functions with the `@bot.command()` decorator in `bot.py`.

### Modifying AI Behavior
Update the `get_ai_response()` method to customize how Gemini AI processes requests and provides responses.

### Database Extensions
Extend the database schema in the `init_database()` function to track additional information.

## Security Notes

- Never commit your `.env` file to version control
- Keep your Discord bot token and Gemini API key secure
- Regularly rotate API keys
- Use role-based permissions to control access

## Troubleshooting

### Common Issues
1. **Bot not responding**: Check bot permissions and token
2. **AI not working**: Verify Gemini API key and quota
3. **Database errors**: Ensure write permissions in bot directory
4. **Role detection failing**: Verify role names match exactly (case-sensitive)

### Logs
The bot prints status information to console. Check for error messages if commands aren't working.

## Support

For issues or feature requests, check the bot's response to commands and console output for debugging information.
