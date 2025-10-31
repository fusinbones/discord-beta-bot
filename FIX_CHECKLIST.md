# ✅ Jim Fix Checklist - Do These Steps

## 🚨 Critical Issues Found:
1. **Duplicate detection was broken** - same content counted multiple times
2. **Scanning entire history** - processing thousands of old messages every 6 hours
3. **Points audit was wrong** - counted duplicates and didn't separate monthly points

## 📋 Fix Steps (Do in Order):

### ☑️ Step 1: Clean Up Existing Duplicates
```bash
python fix_existing_duplicates.py
```
**Wait for it to finish** - it will mark duplicates in the database

### ☑️ Step 2: Restart Jim
Stop and restart the bot to load the fixed code

### ☑️ Step 3: Wait for Auto-Fix
The points audit runs automatically every 2 hours and will correct all points

### ☑️ Step 4: Verify (Optional)
After restart, run:
```
!ambassadors audit
```
This will show you what got fixed

---

## 🎯 What Got Fixed:

✅ Duplicate detection now works correctly  
✅ Only scans last 7 hours of messages (not entire history)  
✅ Points audit excludes duplicates and rejected submissions  
✅ Monthly points vs total points calculated correctly  

---

## 📊 Expected Results:

**Before:**
- Jim adds 100+ rows every few hours
- Same URLs/screenshots counted multiple times
- Points way too high

**After:**
- Only new submissions counted
- Duplicates automatically skipped
- Accurate point calculations
- Logs show "Duplicate skipped" messages

---

## 🔍 How to Monitor:

Watch for these log messages after restart:
- `⚠️ Duplicate URL skipped: username - url...`
- `⚠️ Duplicate screenshot skipped: username - filename`
- `✅ Ambassador sync complete: X messages scanned, Y new submissions processed`

If you see submissions being skipped = **working correctly!**

---

## 📞 If Something's Wrong:

Check `JIM_FIXES_SUMMARY.md` for full technical details

Run these to diagnose:
```
!ambassadors audit          # Check point calculations
!ambassadors sheets-sync    # Force sync to sheets
```
