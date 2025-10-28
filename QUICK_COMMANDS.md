# 🚀 Quick Command Reference for Jim

## Bug Syncing (Simple!)

### **Main Command - Use This One!**
```
!sync-bugs
```
**What it does:** Syncs all new bugs from the database to Google Sheets in one simple command.
- ✅ Automatically prevents duplicates
- ✅ Only syncs bugs that haven't been synced yet
- ✅ Clear success/failure feedback

**Aliases:** You can also use `!syncbugs` (no dash)

---

## Other Useful Commands

### Bug Management
- `!bug [description]` - Report a new bug
- `!find-bug [bug_id]` - Find a specific bug in the database
- `!sheets-resolve [bug_id]` - Mark a bug as resolved in Google Sheets

### Ambassador Commands
- `!ambassadors audit` - Check ambassador points for errors
- `!ambassadors fix-points` - Fix any point calculation issues
- `!ambassadors sheets-sync` - Sync ambassador data to Google Sheets

### Advanced Sync (Usually Not Needed)
- `!resync-bugs` - Force full sync (same as !sync-bugs but longer name)
- `!sync [hours]` - Smart sync for missed bugs from last X hours

---

## 💡 Pro Tips

1. **Just use `!sync-bugs`** - It handles everything automatically
2. The bot syncs bugs automatically, so you usually don't need to run this manually
3. Duplicates are automatically prevented - safe to run anytime
4. If Google Sheets isn't configured, you'll get a clear error message

---

## 🔧 When to Use `!sync-bugs`

- After manually adding bugs to the database
- If you notice bugs missing from the Google Sheet
- After fixing a bug that prevented syncing
- Anytime you want to ensure sheets are up-to-date

**Just remember:** `!sync-bugs` - that's it!
