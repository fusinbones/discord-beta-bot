# 🧪 Test Crisis Support System

## Quick Test Steps

### 1. Restart Jim
```bash
# Stop the bot
# Start the bot again
```

### 2. Go to Support Channel
https://discord.com/channels/906704951202025475/906704950908821507

### 3. Test Crisis Question
Post one of these:
```
"I'm getting a 429 error when linking my closet. Help?"
"My closet keeps asking me to relink. What do I do?"
"I can't log into the app, getting captcha errors?"
```

### 4. Expected Result
✅ Jim replies within 2-3 seconds  
✅ Provides step-by-step instructions  
✅ Includes video links  
✅ Has reassuring footer message  

### 5. Test Staff Escalation
Post something unrelated:
```
"How do I cancel my subscription?"
"What's the refund policy?"
"I need billing help?"
```

### 6. Expected Result
✅ Jim tags @Staff  
✅ Shows embed with your question  
✅ Explains it needs staff assistance  

---

## ✅ It's Working If:
- Jim responds to crisis questions with instructions
- Jim tags staff for non-crisis questions
- Console shows: `✅ Provided crisis support to...`
- Console shows: `⚠️ Escalated to staff...`

## ❌ Something's Wrong If:
- Jim doesn't respond at all
- Jim responds to everything (not filtering)
- Error messages in console

---

## 🎯 One-Liner Test
```
Post in support channel: "I can't link my Poshmark closet?"
```

**Should get full instructions back within seconds!**
