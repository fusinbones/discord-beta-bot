# Google Sheets Integration Setup Guide

This guide will help you set up the Google Sheets integration for Jim's Discord bot bug tracking system.

## Overview

The Discord bot has been integrated with your existing **SDK Issue Log** spreadsheet to provide real-time synchronization of bug reports between Discord and the spreadsheet.

### Features
- ✅ **Auto-sync bug reports** from Discord to spreadsheet
- ✅ **Status updates** when bugs are closed/reopened 
- ✅ **Proper row management** with sequential numbering
- ✅ **Discord reference tracking** in Comments column

## Quick Setup

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the **Google Sheets API**:
   - Go to APIs & Services > Library
   - Search for "Google Sheets API"
   - Click "Enable"

### 2. Service Account Creation

1. Go to **APIs & Services > Credentials**
2. Click **"+ CREATE CREDENTIALS"** > **"Service account"**
3. Fill in service account details:
   - Name: `discord-bot-sheets-access`
   - Description: `Service account for Discord bot Google Sheets integration`
4. Click **"Create and Continue"**
5. Grant roles:
   - **Editor** (or custom role with Sheets access)
6. Click **"Done"**

### 3. Download Credentials

1. In **APIs & Services > Credentials**, find your service account
2. Click the service account email
3. Go to **"Keys"** tab
4. Click **"ADD KEY"** > **"Create new key"**
5. Select **JSON** format
6. Download the JSON file
7. Save it as `service-account-credentials.json` in your bot directory

### 4. Share Spreadsheet Access

1. Open your **SDK Issue Log** spreadsheet
2. Click **"Share"** button
3. Add the service account email (from the JSON file) with **Editor** permissions
4. The email looks like: `discord-bot-sheets-access@your-project.iam.gserviceaccount.com`

### 5. Update Environment Variables

Edit your `.env` file and update these values:

```bash
# The spreadsheet ID is already set correctly
GOOGLE_SPREADSHEET_ID=1msPGQQzQKEiOTjXSX6-zLUXME2KkHJKcF1U9KWb9Gio

# Update this path to your downloaded JSON file
GOOGLE_SHEETS_TOKEN=./service-account-credentials.json
```

## Testing the Integration

Once setup is complete, test the integration:

1. **Restart your Discord bot**
2. **Report a test bug** in Discord: `!bug This is a test bug report`
3. **Check your spreadsheet** - the bug should appear starting at row 30
4. **Close the bug**: `!close-bug [bug_id]` (admin only)
5. **Check spreadsheet** - status should update to "fixed"

## Spreadsheet Structure

The integration works with your existing spreadsheet structure:

| Column | Field | Description |
|--------|-------|-------------|
| A | Row Number | Sequential numbering (auto-assigned) |
| B | Issue Type | Set to "Bug" for Discord reports |
| C | Area | Set to "Discord Bot" |
| D | Description | Bug description from Discord |
| E | Solution | Left blank initially |
| F | Responsible | Left blank initially |
| G | Reported by | Discord username |
| H | Date entered | Timestamp of bug report |
| I | Status | "open" → "fixed" when closed |
| J | Comments | Discord bug ID and channel reference |

## Commands That Sync to Sheets

- `!bug [description]` - Manual bug report (syncs to spreadsheet)
- Auto-detected bugs from keywords (syncs to spreadsheet)
- `!close-bug [id]` - Updates status to "fixed" (admin only)
- `!reopen-bug [id]` - Updates status to "open" (admin only)

## Troubleshooting

### Common Issues

1. **"403 Forbidden" error**
   - Make sure the service account email is added to spreadsheet with Editor permissions
   - Verify the Google Sheets API is enabled in your project

2. **"File not found" error**
   - Check the path to your service account JSON file in `.env`
   - Make sure the file exists and is readable

3. **"Spreadsheet not found" error**
   - Verify the `GOOGLE_SPREADSHEET_ID` in `.env` matches your spreadsheet URL
   - Make sure the service account has access to the spreadsheet

### Getting the Spreadsheet ID

From your spreadsheet URL:
```
https://docs.google.com/spreadsheets/d/1msPGQQzQKEiOTjXSX6-zLUXME2KkHJKcF1U9KWb9Gio/edit
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                    This is your Spreadsheet ID
```

## Security Notes

- Keep your service account JSON file secure and never commit it to version control
- The service account only has access to spreadsheets you explicitly share with it
- Consider using environment variables for sensitive credentials in production

## Support

If you encounter issues:
1. Check the bot's console output for error messages
2. Verify all credentials and permissions are set correctly
3. Test with a simple bug report first
4. Check that the spreadsheet structure matches the expected format (data starting at row 30)

## Success Indicators

✅ Bot starts without Google Sheets errors  
✅ Bug reports appear in spreadsheet starting at row 30  
✅ Status updates when closing/reopening bugs  
✅ Comments column contains Discord bug references  
✅ Row numbers are sequential and auto-assigned  

Once you see these indicators, your Google Sheets integration is working perfectly!
