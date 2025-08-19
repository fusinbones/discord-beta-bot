# Queue Status Command Addition
# Add this to bot.py after the analyze command

@bot.command(name='queue')
async def queue_status(ctx):
    """Check the current analysis queue status"""
    user_id = str(ctx.author.id)
    
    queue_embed = discord.Embed(
        title="📋 Analysis Queue Status",
        color=0x00aaff
    )
    
    # Check if user has a request in queue
    user_in_queue = False
    user_position = 0
    
    for i, item in enumerate(ctx.bot.mentorship_services.analysis_queue):
        if item["user_id"] == user_id:
            user_in_queue = True
            user_position = i + 1
            break
    
    if user_in_queue:
        queue_embed.add_field(
            name="🚀 Your Position",
            value=f"#{user_position}",
            inline=True
        )
        queue_embed.add_field(
            name="⏰ Estimated Wait",
            value=f"~{user_position * 3} minutes",
            inline=True
        )
    else:
        queue_embed.add_field(
            name="📊 Your Status",
            value="No analysis in queue",
            inline=True
        )
    
    # Show total queue length
    total_queue = len(ctx.bot.mentorship_services.analysis_queue)
    queue_embed.add_field(
        name="📈 Total Queue",
        value=f"{total_queue} requests",
        inline=True
    )
    
    # Show processing status
    if ctx.bot.mentorship_services.processing_analysis:
        queue_embed.add_field(
            name="⚙️ Status",
            value="Currently processing analysis",
            inline=False
        )
    else:
        queue_embed.add_field(
            name="⚙️ Status",
            value="Queue idle" if total_queue == 0 else "Ready to process",
            inline=False
        )
    
    # Rate limit info
    if user_id in ctx.bot.mentorship_services.user_last_analysis:
        last_analysis = ctx.bot.mentorship_services.user_last_analysis[user_id]
        time_since = datetime.now() - last_analysis
        remaining = timedelta(hours=1) - time_since
        
        if remaining.total_seconds() > 0:
            minutes_left = int(remaining.total_seconds() / 60)
            queue_embed.add_field(
                name="⏰ Rate Limit",
                value=f"Next analysis available in {minutes_left} minutes",
                inline=False
            )
    
    await ctx.send(embed=queue_embed)
