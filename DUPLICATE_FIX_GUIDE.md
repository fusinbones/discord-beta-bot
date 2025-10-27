# Complete Guide: Fix Duplicate Bugs in Google Sheets

## Problem
Multiple copies of the same bugs are being added to Google Sheets with every sync (every 30 minutes).

## Root Cause
The sync system wasn't tracking which bugs had already been synced, so it tried to add all bugs every time.

## Solution - 3 Steps

### Step 1: Add Tracking Column to Database

Run this script to add a `synced_to_sheets` flag to the bugs table:

```bash
python add_synced_flag.py
```

**What it does:**
- Adds a new column to track which bugs have been synced
- Safe to run multiple times (checks if column exists first)

**Expected output:**
```
🔧 Adding 'synced_to_sheets' column to bugs table...
✅ Successfully added 'synced_to_sheets' column
```

---

### Step 2: Clean Up Existing Duplicates

Run this script to remove duplicate bug entries:

```bash
python cleanup_duplicates.py
```

**What it does:**
- Scans Google Sheets for duplicate bug IDs
- Shows you which duplicates will be deleted
- Keeps the FIRST occurrence of each bug
- Requires confirmation before deleting

**Important:**
- Review the list of duplicates before confirming
- Type `DELETE` exactly to proceed
- Process is irreversible, but keeps first occurrence

**Expected output:**
```
📊 Summary:
   Unique bugs: 277
   Duplicates found: 150

⚠️ WARNING: About to delete 150 duplicate rows:
   - Row 350
   - Row 351
   ... and 148 more

🔴 Type 'DELETE' to proceed with cleanup: DELETE

✅ Deleted row 350 (1/150)
✅ Deleted row 351 (2/150)
...
🎉 Cleanup complete! Deleted 150 duplicate rows
```

---

### Step 3: Restart Jim

Restart the bot to load the new duplicate prevention code.

**What changed:**
1. **Duplicate detection** - Checks if bug exists before adding
2. **Sync tracking** - Marks bugs as synced in database
3. **Smart syncing** - Only syncs bugs that haven't been synced yet

---

## Verification

After restarting Jim, monitor the logs:

### Good Signs ✅

```
📊 Syncing only unsynced bugs (using synced_to_sheets flag)
📋 Found 0 bug(s) to sync
✅ Sync complete: 0 added, 0 skipped (already exist)
```

This means no duplicates are being added!

### Watch For These Messages

**When adding a new bug:**
```
✅ Successfully added bug #278 to Google Sheets
✅ Marked bug #278 as synced in database
```

**During periodic sync (every 30 minutes):**
```
🔍 Checking if bug #278 already exists in spreadsheet...
⏭️ Bug #278 already exists at row 348, skipping duplicate
```

**If you manually run `!resync-bugs`:**
```
📋 Found 0 bug(s) to sync
✅ Sync complete: 0 added, 150 skipped (already exist)
```

---

## New Commands

### `!resync-bugs`
**Staff only** - Force a full sync (with duplicate prevention)
```
!resync-bugs
```

### Testing the Fix

1. **Add a test bug:**
   ```
   !bug This is a test bug to verify no duplicates
   ```

2. **Wait 30 minutes** for the next sync cycle

3. **Check Google Sheets** - the bug should appear only ONCE

4. **Check logs** - should see "skipping duplicate" for existing bugs

---

## If Issues Persist

### Check Database Column

```bash
sqlite3 beta_testing.db "PRAGMA table_info(bugs);"
```

Look for `synced_to_sheets` in the output.

### Manual Reset of Sync Flags

If you need to force a complete resync (after fixing other issues):

```bash
sqlite3 beta_testing.db "UPDATE bugs SET synced_to_sheets = 0;"
```

Then run `!resync-bugs` (but make sure duplicates are cleaned up first!)

### Check Logs

Watch for these potential issues:

❌ **"No synced_to_sheets column"** - Run `add_synced_flag.py` again

❌ **"Bug #X already exists at row Y, skipping duplicate"** - Good! This is working correctly

❌ **Bugs still duplicating** - Check if Jim was restarted with new code

---

## How It Works Now

### When a new bug is reported with `!bug`:

1. Bug saved to database with `synced_to_sheets = 0`
2. Bug added to Google Sheets
3. Database updated to `synced_to_sheets = 1`

### During periodic sync (every 30 minutes):

1. Query: "Get bugs where `synced_to_sheets = 0`"
2. For each bug:
   - Check if exists in sheets (extra safety)
   - If exists, skip
   - If new, add and mark as synced

### Result:
- Each bug synced exactly ONCE
- No duplicates
- Sheet stays clean

---

## Summary

✅ **Fixed:** Duplicate bugs being added every sync  
✅ **Added:** Tracking system to prevent re-syncing  
✅ **Added:** Cleanup script for existing duplicates  
✅ **Added:** `!resync-bugs` command with duplicate prevention  

**Total time to fix:** ~5-10 minutes (most is cleanup script running)
