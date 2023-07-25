"""
The purpose of this script is to torment my coworkers with cringy and irreproducible behavior.
If you are reading this script, congratulations! You understand the codebase
well enough to also torment your coworkers. Feel free to edit this code!

Please don't fire me Brad
"""

#####################
###Version Control###
#####################


#(since I will probably not convince the Carrow lab to use Github)
#Update this string whenever edits are made.

edit_history = """
Version	Initials	Date		Summary
1.0	ARS		25-Jul-2023	First draft is written
"""

import os
import random

#To allow for default behavior, the name variable is established first, 
#then the default behavior (whose fstring needs the name variable)
#then the custom behavior (which overrides the defaults)

#gets name of carrow lab user
username = os.environ.get('USER')
if username == 'arscavuz':
   name = 'Tony'
elif username == 'aplooby':
   name = 'Aidan'
elif username == 'jgarza':
   name = 'Bustin'
else:
   name = username

#default behavior
odds = 0.1
messages = [
f"Haaii! (*^3^)/☆ Let your kawaii spirit shine brightly today, {name}! (^ヮ^)/",
f"(≧ω≦) I believe in you, {name}! You've got this, kawaii superstar~ ☆:.｡.o(≧▽≦)o.｡.:*☆",
f"Ohayou gozaimasu~ (づ｡◕‿‿◕｡)づ Rise and shine, cutie-patootie!",
f"Kawaii alert! ✨(⺣◡⺣)♡* You make everything more adorabe, {name}!",
f"(^-^)/ Yay! {name}'s a weeby wonder! Keep being fabulous~ (^ω^＼)",
f"Omg, you're so UwU-tiful inside and out! (｡♥‿♥｡)",
f"(★ω★)/ Yay, senpai noticed you! Keep shining brightly~ ☆*:.｡.o(≧▽≦)o.｡.:*☆",
f"Hey, hey, kawaii bae~ (灬º‿º灬)♡ Let's rock this day together!",
f"(^-^)/♪♬ {name}, you're the melody in this kawaii symphony of life~ ♬♪(◕‿◕✿)",
f"Boop! (・ω・)ノ Stay cute and stay awesome, {name}!"
]

#custom behavior
#with the exception of the last line, this overrides default behavior
if name == 'Tony':
   odds = 0.5
   #messages = ['new_messages']
   #messages += ['extra_messages']

elif name == 'Aidan':
   odds = 0.00
   #messages = ['new_messages']
   #messages += ['extra_messages']

elif name == 'Bustin':
   odds = 0.00
   #messages = ['new_messages']
   #messages += ['extra_messages']

roll = random.random()
if roll < odds:
   choice = random.randrange(len(messages))
   print(messages[choice])
