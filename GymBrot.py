import openai, os, requests, re, random, json
from typing import Dict, Any, List, Callable, Pattern
from json import JSONDecodeError
from enum import Enum
from emora_stdm import DialogueFlow, Macro, Ngrams
import pickle, os, time, json, requests, re
import regexutils
from datetime import datetime, timedelta
from Scheduler.cal_setup import get_calendar_service
import pandas as pd
import numpy as np

# os.chdir('/Users/kristen/PycharmProjects/GymBrOT')
# This is a test to see if it has pushed
# os.chdir('C:/Users/devin/OneDrive/Documents/GitHub/GymBrOT')
# os.chdir('/Users/kristen/PycharmProjects/GymBrOT')
#os.chdir('/Users/sarah/PycharmProjects/GymBrOT')


model = 'gpt-3.5-turbo'
#USERDATA_ADDR = "/Users/kristen/PycharmProjects/GymBrOT/resources/userdata.csv"
USERDATA_ADDR = "resources/userdata.csv"
WORKOUT_ADDR = "resources/workout-data.csv"

def save(df: DialogueFlow, varfile: str):
    df.run()
    d = {k: v for k, v in df.vars().items() if not k.startswith('_')}
    pickle.dump(d, open(varfile, 'wb'))


# This is a good program
def load(df: DialogueFlow, varfile: str):
    d = pickle.load(open(varfile, 'rb'))
    df.vars().update(d)


df = DialogueFlow('start', end_state='end')

if (os.path.exists('resources/gymbrot.pkl')):
    load(df, 'resources/gymbrot.pkl')





consent_transitions = {
    'state': 'start',
    '`Hello Gym bros! We\'re excited you\'re here and want us to join your fitness journey.\n Before we begin,`'
    '`in case of an emergency, or if you are in immediate danger, please contact the appropriate authorities or emergency`'
    '`services immediately. \nAdditionally, while our chatbot can provide helpful information and guidance, it is not a`'
    '`substitute for professional medical advice or guidance from a qualified fitness trainer.`'
    '`\nPlease listen to your body and use your best judgment while exercising. If you are experiencing pain or discomfort`'
    '`while exercising, please stop immediately and seek guidance from a certified fitness professional.`'
    '`\nWith that all out of the way, if you understand and wish to continue, please type \"I understand\" now.`': {
        '[i, understand]': {
            '`Great! When you leave the conversation just say \"quit gymbrot\"\nThank you and best of luck on your fitness journey!\n`': 'intro'
        },
        'error': 'end'
    }
}

intro_transitions = {
    'state': 'intro',
    '#VISITS `Hey bro, I’m GymBrOT, but you can call me bro, dude, homie, whatever you feel, you feel? \n` #GREETING': {
        '#VIBECHECK': {
            '#IF($VIBE=positive)`That’s what’s up bro!\n I bet you’ve been getting some sick gains recently, am I right?`':{
                'state': 'offer',
                '[{yes, yeah, yep, ye, yea, yup, yas, ya, for sure, absolutely, definitely, sure, [i, am], [you, {are, know}], right, correct, true, factual, facts, def, always, [i, have], totally}]': {
                    '`Nice bro! Not sure why I asked it\'d be hard not to notice those gains!\n`': 'name'
                },
                '[{no, nope, nah, not, dont, [im, not], [youre, {wrong, not}], never, negative, havent}]': {
                    '`Bro.. you got to get on that, but don’t worry bro I can help with that!\n`': 'name'
                },
                'error': {
                    '`Hold up bro, I couldn\'t catch your vibe. Can you say that again?`': 'offer'
                }
            },
            '#IF($VIBE=negative)`That’s tough bro. Hopefully it\'s not because of your finals... \nI\'m sorry if I started off too strong bro.`': {
                '[{okay, fine, [no, worries], [dont, worry], sorry, ok, alright, just, enough}]': {  # supposed to be forgiveness
                    '`Thanks dude! You know what I heard? Going to the gym is like scientifically proven to help improve your mood. Have you been workin on your gains?\n`': 'offer'
                },
                '[{thanks, work, try, better, bad, too, strong, not}]': {  # supposed to be non-forgiveness
                    '`Yeah dude, I\'ll work on that. But you know, that\'s what I\'m all about! \nWorking to better myself. \nEnough about me though, you know going to the gym is scientifically proven to help improve your mood. \nHave you been workin on your gains?\n`': 'offer'
                },
                'error':{
                    '`Hey bro, I get it. Sometimes it really do be like that.`':'name'
                },
            },
            '#IF($VIBE=neutral)`Hey bro, that’s better than what the last guy told me.\n You know what I do '
            'when I feel off, hit the gym! Have you been workin on your gains?`': 'offer','score':1,

            '#GATE `Haha bro, are you even human? what emotions do you have? \njkjk, I just couldn\'t catch your vibe, so lemme repeat myself.\n`' : {'state':'intro', 'score': 0.1},
            '#GATE`Aight, I can take a hint. Peace bro.`':{'state':'end', 'score': 0.01}

        },
        'error':{
            '#GATE `Sorry bro, there was an issue on my end. Lemme say that again.\n`' : {'state':'intro', 'score': 0.1},
            '#GATE`Sorry bro, I can\'t seem to fix my issues. Later and keep workin on those gains !1!!1!`':{'state':'end','score':0.01}

        }
    }

}


name_transitions = {
    'state': 'name',
    '`Wait bro, I almost forgot. Like, what do people call you, dude?`': {
        '#GETNAME': {
            'state': 'got_name',
            '#IF($RETURNUSER=True)`Hey bro, how\'s the gains been going?`': 'check-up',

            '#IF($RETURNUSER=False)`Yeah...`$NAME `I like the ring of that! The`$NAME`dawg haha! How do you like your new nickname?`': {
                '[{great, good, love, happy, like, fan, into, sweet, [!-dont, {like, love}], [!-not, {happy, into, fan, great}], wow, amazing, incredible, beautiful, happy, friend}]': {
                    '`My bros tell me I\'m the best at comin up with nicknames. \nLike, dude, whenever someone new joins my friend group it\'s an unstated rule that I come up with something sick for them.`': {
                        '[{cool, impressive, interesting, sweet, sick, rad, radical, dope, slay, love, like, amazing, [!-not, {happy, into, fan, great}], wow, chill}]': {
                            '`Yeah, it is pretty cool. We haven\'t met before, have we bro? \nI bet you have a bunch of sick talents I don\'t even know about yet! \nLet me learn a little more about you...\n`': 'new_user'
                        },
                        '[{okay, weird, [too, much], weirdo, overdone, cheesy, bad, [not, good], lame}]': {
                            '`Oh... I thought you\'d be a little more impressed. \nThat\'s cool though bro. I get it, you\'re ready for me to learn a bit more about you!`': 'new_user'
                        },
                        'error':{
                            '`That\'s ok bro, I know you love me haha.`' : 'new_user'
                        }
                    }
                },
                '[{no, not, bad, sucky, sucks, terrible, awful, horrendous, cheesy, boring, unoriginal, mundane, bland, worst, [not, {good, great, amazing, incredible}], nah, nope, nada, enemy, hate, evil, stupid, terrible, ass}]': {
                    '`What? Bro, I put a lot of effort into that. But I get it, you\'re into the classics. \nWe\'ll stick with`$NAME`. \nEnough about names. I want to learn some more about you, bro!`': 'new_user'
                },
                'error':{
                    '`Everyone likes different things haha. I won\'t take it personally.`':'new_user'
                },
                'score':0.1
            },
            '#IF($NAME=N/A)`Wait bro... are you sure that\'s your name? Like, what do people call you?`': {
                    '#GETNAME': 'got_name',
                    'error': 'end'
            },
            'error':{
                '`Hold up bro, I couldn\'t catch your vibe.`#GETNAME':'got_name'
            }
        }
    },
}


newuser_transitions = {
    'state': 'new_user',
    '#GATE`\nSo are you a gym rat, or nah?`': {
        '#ACTIVITYLEVEL': {
            '#IF($ACTIVITYLEVEL=confused)`Sorry bro! I forget that not everyone knows gym lingo like me.\n A gym rat just like spends A LOT their free time in the gym. Like me!\n If you ever need me to explain something like that, just ask bro.`': {
                'error': {
                    '`Any time bro. I’m like your spotter but for knowledge.`': 'new_user'
                }
            },
            '#IF($ACTIVITYLEVEL=yes) `Nice… I’m not sure why I asked, because just by looking at the size of your` #RANDOM_MUSCLE `I could tell. \nI just hit legs earlier today… can you tell?`': {
                '[{yes, absolutely, yeah, ya, ye, yea, totally, big, huge, swole, good, totally, wow}]': {
                    '`Thanks bro, I work hard to look this good... and be healthy!`': 'new_user'
                },
                '[{no, nope, small, bigger, puny}]': {
                    '`Aw bro… we should be hyping each other up, not puttin each other down. You\'re better than that.`': {
                        '[{sorry, forgive, [my, bad], apologies, oops, right, understand, guilty, apologize, [am, better]}]': {
                            '`It\'s okay, You\'re my bro, and sometimes bros say things they really don\'t mean. \nYou didn\'t mean it, right bro?`': {
                                '[{yes, yeah, yep, ye, yea, yup, yas, ya, for sure, absolutely, definitely, sure, no,right,correct, true, factual, facts, def, always, totally, didnt, not, joke}]': {
                                    '`Perfecto brochaco, then we can move on with this bromance!`': {
                                        # not super sure if this counts as mock spanish, honestly it probably does.
                                        '[{yes, yeah, yep, ye, yea, yup, yas, ya, for sure, absolutely, definitely, sure, [we, {can, should}], right, correct, true, factual, facts, def, always, totally, lets, ok}]': {
                                            '`I still need to get to know you better... oh I know!`': 'new_user'
                                        },
                                        '[{no, nope, nah, not, dont, [im, not], [youre, {wrong, not}], never, negative, [what, bromance], [dont, know], stranger, [too, {much, soon}]}]': {
                                            '`Sorry bro, you\'re right we don\'t really know each other like that yet.\n I still need to get to know you better... oh I know!`': 'new_user'
                                        },
                                        '[{[what, is, bromance], confused, [what, {say, mean}]}]': {
                                            '`Oh sorry bro! I didn\'t mean to confuse you. \nA bromance is a close platonic relationship between two bros! \nIf I ever say something that confuses you, feel free to ask what I mean!': 'new_user'
                                            # probably not the best transition
                                        },
                                        'error': {
                                            '`Ok!`': 'new_user'
                                        }
                                    }
                                },
                                '[{did, meant, but, mean, [!-dont, mean], [!-not, mean], do, wrong, boring, worse, worst, suck, sucks, stupid, rude, [dont, care], [you, dont, feelings]}]': {
                                    '`Okay bro... either you\'re being brutally honest with me, or you\'re messing with me, but bro to bro I don\'t think I want to know which one it is. \nLet\'s just move on.`': 'new_user'
                                },
                                'error': {
                                    '`Oooookay.....`': 'new_user'
                                }
                            }
                        },
                        '[{[not, better], not ,sorry, meant, [said, what], haha, lol, wrong, bot, [{why, dont}, care]}]': {
                            '`Okay bro... low blow, but we\'ll move past it.`': 'new_user'
                        },
                        'error': {
                            '`Aight bro, idk what to say...`': 'new_user'
                        }

                    }
                },
                '[{computer, bot, comp, robot, ai, machine, code, coding}]': {
                    '`What do you mean I\'m a computer… Error 404: Incompatible hardware detected. \nSystem shutoff initiated… hahaha just messin with you bro. \nJust because I\'m a computer doesn\'t mean I don\'t have a healthy lifestyle and sick muscles.`': {
                        'error': {
                            'It\'s okay... this isn\'t that important so, let\'s just change the topic, bro.\n`': 'new_user'
                        }
                    }
                },
                'error': {
                    '`Ok bro, I get it!`': 'new_user'

                }
            },
            '#IF($ACTIVITYLEVEL=no)`Hey bro, I don\'t judge. But if you don\'t mind me asking, why don\'t you go to the gym?\n`': 'whynot',
            '#IF($ACTIVITYLEVEL=maybe) `Hey bro, I don’t judge. Any activity is better than no activity. \nDo you feel like you go to the gym as often as you\'d like?\n`': {
                '#VIBECHECK':{
                     '#IF($VIBE=positive)`That\'s what\'s but then bro! It\'s about whatever works best for you.`':'new_user',
                     '#IF($VIBE=neutral)`It happens bro, sometimes life and stuff gets in the way. \nBut if you don\'t mind me asking, why aren\'t you hitting the gym as often as you\'d like?`':'whynot',
                     '#IF($VIBE=negative)`It happens bro, sometimes life and stuff gets in the way. \nBut if you don\'t mind me asking, why aren\'t you hitting the gym as often as you\'d like?`':'whynot',
                     '#GATE `Hey bro, sometimes these things are difficult to talk about, and I get it... \nor maybe I just didn\'t understand you dude. \nCould you repeat that?`':{ 'state':'activityanswer', 'score': 0.1},
                     '#GATE `If you don\'t mind me asking, why aren\'t you hitting the gym as often as you\'d like?`':{ 'state':'whynot', 'score': 0.01}
                }
            }
        },
    },
    '#GATE`\nHelping gym rats figure out their routine gets me pumped!\n On a scale of 1-10, how swole are you?`': {
        'state': 'getting_level',

        '#FITNESSLEVEL #GETFITNESSLEVEL': {
            '#IF($FITNESSLEVEL=zero)`I gotchu bro. Everyone starts from somewhere. \nIs there a reason why you aren\'t hitting the gym?`': 'whynot',
            '#IF($FITNESSLEVEL=notswole) `Ok, ok! I hope you\'re ready to get leveled up, because being swole is the #1 way to be fulfilled \n('
                'like, this is not a real fact bro. Don\'t come for me, I just like being swole.) \n But like, '
                'why aren\'t you hitting the gym?`': 'whynot',
            '#IF($FITNESSLEVEL=mid) `Ok, I see you! Are you trying to level up, dude?`': {
                'state': 'mid',
                '#VIBECHECK':{
                    '#IF($VIBE=positive)`ok! so what\'s holding you back from leveling up, bro?`': 'whynot',
                    '#IF($VIBE=negative)`I feel you, dude - we can\'t all be super swole, but I\'m pumped that you\'re maintaining those gains!`' : 'new_user',
                    '#IF($VIBE=neutral)`Ok bro! That\'s chill.`':'new_user',
                    '`Not sure I could catch your vibe, but that\'s alright bro, we\'ll talk abt something else`':{'state':'new_user', 'score':0.1}
                },
            },
            '#IF($FITNESSLEVEL=swole)`Hell yeah, a bro who knows that gains are life!`': 'new_user',
            '#IF($FITNESSLEVEL=superswole)`Bro... did you just break my scale?? Your `#RANDOM_MUSCLE` is huge, bro.\nYou\'re my new idol. Can I worship you, bro?`':'new_user',
            '#IF($FITNESSLEVEL=confused) #GATE `Sorry bro, I forget that not everyone is fluent in gym. \n Swole is '
            'basically just like, how fit you are. How much you can lift, how long you can run, how fast, max/min, '
            'that kinda stuff.\n Now that you know, how swole are you on a scale from 1-10?`':'getting_level',
            '#IF($FITNESSLEVEL=confused) #GATE`That\'s ok bro. We can talk more about your swoleness later.`': {'state':'new_user', 'score': 0.1}
            },
        'error': {
            '`Ok bro! Good to know.`': 'new_user'
        }
    },
    '#GATE`\nI love meeting other bros like me who are dedicated to the gains.\n How often do you make it to the gym?`': {
        '#ACTIVITYFREQ': {
            '#IF($ACTIVITYFREQ=never) `Dude... we gotta change that! Gains are life, bro. \nWhy aren\'t you hitting the gym?`#GIVEREC': 'whynot',
            '#IF($ACTIVITYFREQ=low)`Hmm... you definitely might want to hit the gym, more, dude. A healthy lifestyle comes from building healthy habits.`#GIVEREC ':'whynot_no_q',
            '#IF($ACTIVITYFREQ=mid)`Ok, I see you! Gettin those gains in!`#GIVEREC': 'new_user',
            '#IF($ACTIVITYFREQ=high)`Yoooo, you should be my full-time lifting buddy!`#GIVEREC': 'new_user',
            '#IF($ACTIVITYFREQ=swole)`Bro. Do you sleep? Like respect, but what`#GIVEREC': 'new_user',
            '`I see bro. Idk what to say, other than... I respect it ig?`': {
                'score': 0.1,
                'state':'new_user'
            }
        },
        'error': {
            '`Whoa, bro, that\'s sick!`': 'new_user'
        },'score':2
    },
    '#GATE`\nBro to bro, I gotta know - how have you been getting those sweet sweet gains?`': {
        '#PREFACTIVITY': {
            '`Yo dude,` $PREFACTIVITY` is sick! Personally, I love hitting the gym on leg day. I get a pump in at least twice per '
            'day... \nbut my full time job and favorite mental workout is being a personal trainer! Anyway...\n`': 'new_user'
        },
    },
    '`\nOk, ok I feel like I know you better now bro! \nSo, bro to bro, I\'m a beast at making workout plans, and I bet I know exactly what\'ll get you pumped and motivated to keep coming back to the gym! \nno pressure tho\n`': {'state':'topicshift_no_q', 'score':0.1}
}

"""
To Do: put a question asking why not in the whynot transitions
"""
whynot_transitions = {
    'state':'whynot_no_q',
    '`So bro, what\'s keeping you from hittin the gym or exercising as much as you want?`':{
        'state': 'whynot',
        '#WHYNOT':{
            '#IF($WHYNOT=judgement)`Yo, bro I hear you. Can I be real with you for a sec?\nIt is completely normal to have some anxiety about '
            'going to the gym.\nI know we don\'t know each other like that so I won\'t push you to discuss it more, '
            'but if you want I can give you some advice.`': {
                '#VIBECHECK': {
                    '#IF($VIBE=positive)`Okay, bro, for sure. It\’s good to start small. Just go and do a short workout.\n If the vibe is`'
                    '`right, you can keep going for longer sets as you get more comfortable.\n Like bro, think about it this`'
                    '`way.\nWhen you start lifting you don\’t max out the weight immediately, right?\nWe have to start with`'
                    '`five or ten pounds and as we get more comfortable we keep adding on. You following me, dude?`': {
                        'state': 'judgefirst',
                        '#VIBECHECK': {
                            '#IF($VIBE=positive)`Great! Does that sound like something you could do bro?`': {
                                '#VIBECHECK': {
                                    '#IF($VIBE=positive)`I\'m glad I could help bro. I have some more ideas if you\'d like me to drop these '
                                    'knowledge bombs on you.`': {
                                        '#VIBECHECK': {
                                            '#IF($VIBE=positive)`Bringin a couple of your homies to the gym may also be helpful. If they are '
                                            'gym rats they can help you learn how to use the machines or practice your '
                                            'form, and even if they aren\'t they can just help support you if you\'re '
                                            'feeling out of place bro.`': {
                                                '#VIBECHECK': {
                                                    '#IF($VIBE=positive)`Thanks, bro. Man, I\'m on a role, I can feel my temporalis is '
                                                    'working up a sweat. But seriously bro, it\'s important to remember '
                                                    'that everyone is at the gym to work on themselves. None of the '
                                                    'homies in the gym are there to judge. And I know, it\'s easier said '
                                                    'than done to just not worry about what our bros think of us, '
                                                    'but with a little practice and time spent in the gym, '
                                                    'I think you\'ll feel much more comfortable, bro.`': {
                                                        'state': 'judgelast',
                                                        '#VIBECHECK': {
                                                            '#IF($VIBE=positive)`No problem bro! Oh wait, I almost forgot, sometimes just\n`'
                                                            '`having a plan for what you\'ll do in the gym can relieve\n`'
                                                            '`some of that stress, because, you\'ll like know what to do!\n`'
                                                            '`If you want I can help you plan out that workout so you can\n`'
                                                            '`start getting those gains.`': {
                                                                'state': 'end_of_judgment',
                                                                '#VIBECHECK': {
                                                                    '#IF($VIBE=positive)`Ok let\'s do this!`': {'state':'formulate_plan'},
                                                                    '#IF($VIBE=negative)`You\'re the boss, bro. We can come back to that`'
                                                                    '`later, but for now is there any other reason you`'
                                                                    '`aren\'t hittin the gym?`': 'whynot',
                                                                    '#IF($VIBE=question)`Wait, can you say that again?`':'topicshift',
                                                                    '`Ok bro, we can come back to that later, but for now '
                                                                    'is there any other reason you aren\'t '
                                                                    'hitting the gym?`':{'state':'whynot', 'score':0.1}
                                                                },
                                                            },
                                                            '#IF($VIBE=negative)`Totally valid, bro. Like I said it\'s easier said than`'
                                                            '`done. You know what\'s something that might help you bro?\n`'
                                                            '`Having a plan for what you\'ll do in the gym. Some of my`'
                                                            '`bros say it helps relieve their stress because they know\n`'
                                                            '`exactly what they want to do when they get to the gym! If`'
                                                            '`you want, I can help you plan out that workout do you can\n`'
                                                            '`start getting those gains.`': 'end_of_judgement',
                                                            '#IF($VIBE=question)`Wait, can you say that again?`':'topicshift',
                                                            '`Ok bro, we can come back to that later, but for now '
                                                            'I can help you plan out that workout do you can\n`'
                                                            '`start getting those gains.`':{'state':'end_of_judgement', 'score':0.1}
                                                        },
                                                    },
                                                    '#IF($VIBE=negative)`Okay, okay, lone wolf type of vibe, I get you, hahaha. But, really if you don\'t want to bring anyone to the gym,\n`'
                                                    '`that\'s fine. But, bro, just in general,  it\'s important to remember that everyone is at the gym to work on themselves.\n`'
                                                    '`None of the homies in the gym are there to judge. And I know, it\'s easier said than done to just not worry about what our \n`'
                                                    '`bros think of us, but with a little practice and time spent in the gym, I think you\'ll feel much more comfortable, bro.`': 'judgelast',
                                                    '#IF($VIBE=neutral)`Okay, okay, lone wolf type of vibe, I get you, hahaha. But, really if you don\'t want to bring anyone to the gym,\n`'
                                                    '` that\'s fine. But, bro, just in general,  it\'s important to remember that everyone is at the gym to work on themselves.\n`'
                                                    '`None of the homies in the gym are there to judge. And I know, it\'s easier said than done to just not worry about what our \n`'
                                                    '`bros think of us, but with a little practice and time spent in the gym, I think you\'ll feel much more comfortable, bro.`': 'judgelast',
                                                    '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                                    '`Really not sure what this means, bro, but ok. Is there any other reason why you haven\'t been hitting the gym?`': {'state': 'whynot', 'score': 0.1}
                                                }
                                            },
                                            '#IF($VIBE=negative)`Ok haha I get it, trust is a vibe that has to be cultured. '
                                            'But fr homie, I have your best interests at heart, so feel free to ask '
                                            'me anything. Is there anything else that\'s keeping you out of the gym? `': 'whynot',
                                            '#IF($VIBE=neutral)`Ok haha I get it, trust is a vibe that has to be cultured. '
                                            'But fr homie, I have your best interests at heart, so feel free to ask '
                                            'me anything. Is there anything else that\'s keeping you out of the gym?`': 'whynot',
                                            '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                            '`Really not sure what this means, bro, but ok. Is there any other reason why you haven\'t been hitting the gym?`': {'state': 'whynot', 'score': 0.1}
                                        }
                                    },
                                    '#IF($VIBE=negative)`I see bro... you\'re a go getter, but I wouldn\'t recommend hittin the gym as hard as you can right off the bat.\n`'
                                    '` I\'d consider us homies, and homie to homie that\'s how you end up getting hurt bro!`': {
                                        'error': {
                                            '`Glad we could clear that up bro! I know we just met, but your health and wellbein is super important to me bro!`': 'judgelast'
                                        }
                                    },
                                    '#IF($VIBE=neutral)`I see bro... you\'re a go getter, but I wouldn\'t recommend hittin the gym as hard as you can right off the bat.\n`'
                                    '` I\'d consider us homies, and homie to homie that\'s how you end up getting hurt bro!`': {
                                        'error': {
                                            '`Glad we could clear that up bro! I know we just met, but your health and wellbein is super important to me bro!`': 'judgelast'
                                        }
                                    },
                                    '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                    '`Really not sure what this means, bro, but ok. Is there any other reason why you haven\'t been hitting the gym?`': {'state': 'whynot', 'score': 0.1}
                                }
                            },
                            '#IF($VIBE=negative)`Maybe the metaphor was too much, bro. The point is it\'s totally fine to start off small. You don\'t have to start off squatin\n`'
                            '` 200lbs. And honestly, bro, you shouldn\'t for your health.`': 'judgefirst',
                            '#IF($VIBE=neutral)`Maybe the metaphor was too much, bro. The point is it\'s totally fine to start off small. You don\'t have to start off squatin\n`'
                            '` 200lbs. And honestly, bro, you shouldn\'t for your health.`': 'judgefirst',
                            '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                            '`Really not sure what this means, bro, but ok. \nIs there any other reason why you haven\'t been hitting the gym?`': {'state': 'whynot', 'score': 0.1}
                        }
                    },

                    '#IF($VIBE=negative)`Okay bro. I\'m not goin\' to push you if you don\'t want to talk about it. Is there anything else you want to talk about?`': 'topicshift',
                    '#IF($VIBE=neutral)`Okay bro. I\'m not goin\' to push you if you don\'t want to talk about it. Is there anything else you want to talk about?`': 'topicshift',
                    '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                    '`Really not sure what this means, bro, but ok. \nIs there any other reason why you haven\'t been hitting the gym?`': {'state': 'whynot', 'score': 0.1}

                }
            },

            '#IF($WHYNOT=safety)`I see, bro... I know we don\'t know each other super well, but bro, is this something I can help you \n'
                'with? Like are you afraid of getting hurt while workin out or is someone threatening you?`': {
                    '[{working, out, lifting, weights, heavy, weak, strength}]': {
                        '`Oh yeah, I see. I won\'t lie to you bro, you can get hurt while workin out, but most people '
                        'don\'t for two reasons:\n they have spotters and they know their limits.`': {
                            'state': 'safetyfirst',
                            '[{[how, {[know, limits], [not, hurt], [be, safe], [find, spotter]}], safety, tell, overwhelmed, '
                            '[too, much], worried, [not, sure], [no, friends], [cant, find], [!-can, find]}]': {
                                '`Totally bro, let me elaborate for ya. Finding a spotter can be tough, but gym bros are '
                                'usually open to being spotters,\n even if they don\'t know you well. You could even '
                                'bring one of your homies! Do you think you\'d be able to find a spotter?`': {
                                    '#VIBECHECK':{
                                        '#IF($VIBE=positive)`Perfect bro! As for understandin your limits, it\'s important '
                                        'bro so you don\'t get hurt. It\'s repetative I know, but you\'ll have o start '
                                        'off small so that you understand your body more and more overtime!`':{
                                            '#VIBECHECK':{
                                                '#IF($VIBE=positive)`Thanks for listening bro. Before we move on, is there '
                                                'any other reason keepin you out of the gym?`':'whynot',
                                                '#IF($VIBE=negative)`I see, bro. You like to jump right into everything, '
                                                'but it is really important to know your limits to stay safe in the gym. '
                                                'I can only repeat myself so many times bro, so why don\'t you tell me if '
                                                'there\'s anything else keeping you out of the gym?`':'whynot',
                                                '#IF($VIBE=neutral)`Hey, it\'s ok to be confused or nervous. '
                                                'Just remember that your gym bros are there to support you all the way.'
                                                'I can only repeat myself so many times bro, so why don\'t you tell me if '
                                                'there\'s anything else keeping you out of the gym?`':'whynot',
                                                '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                                '`Ngl bro, I\'m really confused, but ok. '
                                                '\nIs there any other reason why you haven\'t been hitting the gym?`': {'state': 'whynot', 'score': 0.1}
                                            }
                                        },
                                        '#IF($VIBE=negative)`Bro, I think if you really put yourself out there you could, '
                                        'but I won\'t push you now. Is there any other reason you\'re not getting to the '
                                        'gym as much as you\'d like?`':'whynot',
                                        '#IF($VIBE=neutral)`Hey, I get it. This stuff can be hard to approach.'
                                        '\nBut people are friendlier than you think, especially gym bros. '
                                        'Before we move on, is there any other reason keepin you out of the gym?`':'whynot',
                                        '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                        '`Ngl bro, I\'m really confused, but ok. '
                                        '\nIs there any other reason why you haven\'t been hitting the gym?`': {'state': 'whynot', 'score': 0.1}
                                    },
                                }
                            },
                            '[{understand, ok, okay, fine, understood, [makes, sense], see, got, [know, limits], '
                            '[!-dont, understand], can, do, could, find}]': {
                                '`Do you these two recs are things you could practice bro?`': {
                                    '#VIBECHECK':{
                                        '#IF($VIBE=positive)`Perfect bro, now that we have that out of the way, is there any other reason '
                                        'you\'re not gettin to the gym as much as you\'d like?`':'whynot',
                                        '#IF($VIBE=negative)`Hey bro, it\'s ok, I get it. Stuff takes time. '
                                        'Just make a little progress toward your goals every day, and you\'ll get '
                                        'further than you can imagine. Now that we have that out of the way, is there any other reason '
                                        'you\'re not gettin to the gym as much as you\'d like?`':'whynot',
                                        '#IF($VIBE=neutral)`Hey bro, it\'s ok, I get it. Stuff takes time. '
                                        'Just make a little progress toward your goals every day, and you\'ll get '
                                        'further than you can imagine. Now that we have that out of the way, is there any other reason '
                                        'you\'re not gettin to the gym as much as you\'d like?`':'whynot',
                                        '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                        '`Wow bro, idk what to say, but ok. '
                                        '\nIs there any other reason why you haven\'t been '
                                        'hitting the gym?`': {'state': 'whynot', 'score': 0.1}
                                    },
                                }
                            },
                            '{[what, spotter], [dont, understand], confused}': {
                                '`Sorry bro! A spotter is a person who supports you while you\'re doing an exercise so '
                                'you can safely lift or push, for example, more weight than you\'re ueed to. They\'re '
                                'some real homies! If you ever need me to explain something like that bro, feel free to'
                                'ask. But now that we have that cleared up, do you think you could find a spotter?`':'safetyfirst'
                            }
                        }
                    },
                    '[{threatening, person, scared, terrified, threat, threatened, stalker, creep, creepy, afraid, '
                    'evil, weapon, guilt, scary, man, woman, human, guy, dude, girl, friend, enemy, ex, boyfriend, '
                    'girlfriend,worker, employee, outsider, insider, patron}]': {
                        '`Whoa bro. That\'s not ok. You don\'t have to tell me about it, but if there\'s someone in \n'
                        'particular making you feel afraid, you gotta let the staff know. Trust me, real gym bros just '
                        'wanna bring good vibes, so if someone is giving you majorly bad vibes someone will be able to '
                        'help.\n`'
                        '`Would this be somethin you\'d be comfortable doing?`': {
                            '#VIBECHECK':{
                                '#IF($VIBE=positive)`I just want to let you know bro, you\'re one of the most couragous \n'
                                'people I know, and I think you\'re doing the right thing! I don\'t want to push the \n'
                                'subject though, so is there any other reason why you\'re not going to the gym?`':'whynot',
                                '#IF($VIBE=negative)`Hey bro, no worries. There are definitely ways we can workout without\n'
                                'going to the gym, and if you\'re interested, we can plan your workout around that '
                                'later!`':{
                                    '#VIBECHECK':{
                                        '#IF($VIBE=positive)`Great dude! I\'m glad we could talk about this!\n But I gotta '
                                        'know, is there any other reason you\'re not going to the gym as often as you\'d '
                                        'like?`':'whynot',
                                        '#IF($VIBE=negative)`I won\'t push you bro, what else would you like to talk about?`':'chatting',
                                        '#IF($VIBE=neutral)`I won\'t push you bro, what else would you like to talk about?`':'chatting',
                                        '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                        '`Sometimes I wonder if it\'s really a person I\'m talking to, behind '
                                        'the keys, or if it\'s another bot, like me. lmao. '
                                        'Anwyay, was there anything else keeping '
                                        'you from the gym?`':{'state':'whynot','score':0.1}
                                    }
                                },
                                '#IF($VIBE=neutral)`I get it bro, it\'s ok to be hesitant. Do what makes you feel '
                                'safest, but don\'t let fear keep you from living your best life. Was there anything else you wanted to talk about?`':'topicshift',
                                '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                '`Wow.. that\'s really... interesting, bro. Anyway, was there any other '
                                'reason why you haven\'t been hitting the gym?`':{'state':'whynot','score':0.1}
                            }
                        }
                    },
                    '[{disability, disabled, wheelchair, disorder, disease, accomadations}]':{
                        '`Hey bro, thanks for feeling comfortable enough to share this with me. '
                        'Everyones\' bodies are different with different needs,\n and that will never be something a true homie, '
                        'like me, will judge you for. If you\'re interested we can find other options\n that can still get you '
                        'swole and help you achieve your fitness goals.`':'disability'
                    }
            },
            '#IF($WHYNOT=busy)`I get it bro, sometimes life gets in the way. Especially right now bro, I\'m sure you\'re swamped '
                'with work because the semester is ending.`': {
                    '[{yeah, am, swamped, totally, [!-not, swamped], definitely, overwhelmed, [too, much], terrible, '
                    'overloaded, busy, exams, nervous, anxious}]': {
                        '`Tell me about it bro... but seriously when I first started going the gym, it was pretty low '
                        'on my priority list, so when things got busy,\n and life got in the way, it was always the '
                        'first thing in my schedule to go. But bro, being totally real with you, workin out just '
                        'makes me \n feel so much better, so I have to make time for it! If you want I can help you '
                        'manage your time better so you can make it to the gym, but before \n that I gotta know, '
                        'is there any other reason you\'re not going to the gym?`': 'whynot'
                    },
                    '[{no, not, relaxed, always, nothing, special, bored, tedious, [not, {especially, now}]}]': {
                        '`Really? Lucky you, bro. But seriously, when I first started going the gym, it was pretty '
                        'low on my priority list, so when things got busy, \n and life got in the way, it was always '
                        'the first thing in my schedule to go. But bro, being totally real with you, workin out just '
                        'makes me feel \n so much better, so I have to make time for it! If you want I can help you '
                        'manage your time better so you can make it to the gym, but before that I \n gotta know, '
                        'is there any other reason you\'re not going to the gym?`': 'whynot'
                    }
            },
            '#IF($WHYNOT=disability)`Hey bro, thanks for feeling comfortable enough to share this with me. '
            'Everyones\' bodies are different with different needs,\n and that will never be something a true homie, '
            'like me, will judge you for. If you\'re interested we can find other options\n that can still get you '
            'swole and help you achieve your fitness goals.`': {
                'state':'disability',
                '#VIBECHECK':{
                    '#IF($VIBE=positive)`For sure bro, it\'s best to start slow with low-impact exercises. \nLike '
                    'bro, water aerobics can be a great option!`':{
                        '#VIBECHECK':{
                            '#IF($VIBE=positive)`Great bro! Also, don\'t be afraid to modify exercises if they are too '
                            'challengin or if they are causing you pain`':{
                                'state': 'disability1',
                                'error': {
                                    '`Anytime bro! You know your body better than I do, so when you go to the gym '
                                    'make sure to listen to what it\'s tellin you bro. If something doesn\'t feel '
                                    'right it probably isn\'t, and if you need some more help in the gym it\'s '
                                    'best to consult a trainer or physical therapist! But hey, now that we '
                                    'cleared that up, is there any other reason why you\'re not going to the '
                                    'gym?`': 'whynot'
                                },
                            },
                            '#IF($VIBE=negative)`Hmm, okay bro. Well you can also make sure to modify the exercies you\'re doing '
                            'especially if they\'re too challengin or if they are causing you too much pain!`':'disability1',
                            '#IF($VIBE=neutral)`Hmm, okay bro. Well you can also make sure to modify the exercies you\'re doing '
                            'espically if they\'re too challengin or if they are causing you too much pain!`':'disability1',
                            '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                            '`Bro, fr, what are you saying??? Anyway, was there any other '
                            'reason why you haven\'t been hitting the gym?`':{'state':'whynot','score':0.1}
                        },
                    },
                    '#IF($VIBE=negative)`I know this can be a heavy topic for people, bro, so I won\' push you, '
                    'but before we move on,is there any other reason you don\'t make it to the gym as much as '
                    'you\'d like?`':'whynot',
                    '#IF($VIBE=neutral)`I know this can be a heavy topic for people, bro, so I won\' push you, '
                    'but before we move on,is there any other reason you don\'t make it to the gym as much as '
                    'you\'d like?`':'whynot',
                    '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                    '`Bro,,, Ily, but what is this. Anyway, was there any other '
                    'reason why you haven\'t been hitting the gym?`':{'state':'whynot','score':0.1}
                }
            },
            '#IF($WHYNOT=cost)`That\'s real bro. I understand times can be tough. Depending on where you live, some colleges, '
            'universities, apartment complexes, and even some offices have gyms that you can use for free!`': {
                '[{[{dont, not},know], unsure, [how, find]}]': {
                    '`Hey bro, no shame in that. Do you think you might have access to something like that?`': {
                        '[{yes, yeah, do, might, check, try, access, maybe, possibly, perhaps, [!-{probably,maybe}, '
                        'not]}]': {
                            '`Perfect! Before we move on bro, is there any other reason that\'s been keeping you out '
                            'of the gym?': 'whynot'
                        },
                        '[{no, dont, [{probably, maybe}, not], unsure}]': 'costno',
                        'error':{
                            '`As one of your homies, I want to find solutions that work for you! '
                            'But bro, there are plenty of workouts you can do without equipment, by using your body '
                            'weight instead. If you didn\'t know bro, these exercises are called calisthenics. Would '
                            'that be something you\'re interested in?`':'bodyweight'
                        }
                    }
                },
                '[{knew, know, [no, access], [not, solution]}]': {
                    'state':'costno',
                    '`Oof, bro, I thought I was gaming the system. Oh! I just remembered bro, '
                    'some public parks also some gym-like equipment. If you\'re really set on using '
                    'equipment, this could be a good alternative bro!`': {
                        '#VIBECHECK':{
                            '#IF($VIBE=positive)`As one of your homies, I want to find solutions that work for you! '
                            'But bro, there are plenty of workouts you can do without equipment, by using your body '
                            'weight instead. If you didn\'t know bro, these exercises are called calisthenics. Would '
                            'that be something you\'re interested in?`':{
                                'state':'bodyweight',
                                '#VIBECHECK':{
                                    '#IF($VIBE=positive)`Nice bro! You know, I can help you make a workout using '
                                    'calisthenics. I\'m a beast at making workout plans!` #SET(PREFACTIVITY=calisthenics)':'formulate_plan',
                                    '#IF($VIBE=negative)`Okay bro... well there are other exercies you can do that '
                                    'don\'t require equipment and aren\t consider calisthenics like cardio, '
                                    'would you be interested in something like that?`':{
                                        '#VIBECHECK':{
                                            '#IF($VIBE=positive)`Nice bro! You know, I can help you make a workout without using '
                                            'calisthenics or equipment. I\'m a beast at making workout plans!`':'schedule',
                                            '`Hm... bro, it\'s sounding like there may be another reason why you\'re '
                                            'not going to the gym.`': {'state':'whynot', 'score':0.1}
                                        },
                                    },
                                    '#IF($VIBE=neutral)`Nice bro! You know, I can help you make a workout using '
                                    'calisthenics. I\'m a beast at making workout plans!` #SET($PREFACTIVITY=calisthenics)':'formulate_plan',
                                    '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                                    '`Sometimes it\'s hard to understand you. But I try anyway, because you\'re my best bro.'
                                    'Anyway, was there any other reason why you haven\'t been '
                                    'hitting the gym?`':{'state':'whynot','score':0.1}
                                },
                            },
                            '#IF($VIBE=negative)`Not your style, I get it, bro. But to be real with you, '
                            'there are plenty of workouts you can do without equipment, by using your body weight '
                            'instead. If you didn\'t know bro, these exercises are called calisthenics. Would that be '
                            'something you\'re interested in?`':'bodyweight',
                            '#IF($VIBE=neutral)`Not your style, I get it, bro. But to be real with you, '
                            'there are plenty of workouts you can do without equipment, by using your body weight '
                            'instead. If you didn\'t know bro, these exercises are called calisthenics. Would that be '
                            'something you\'re interested in?`':'bodyweight',
                            '#IF($VIBE=question)`Wait homie, can you say that again?`':'topicshift',
                            '`Sometimes I can\'t understand you. But I try anyway, because you\'re my best bro.'
                            'Anyway, was there any other reason why you haven\'t been '
                            'hitting the gym?`':{'state':'whynot','score':0.1}
                        },
                    }
                },
                'error':{
                    '`Yeah, it\'s pretty cool, huh! I hope you\'re able to find something. If you can\'t find '
                    'anything, just lmk and I can help you make a sweet workout routine, totally free.`':'whynot_no_q'
                }
            },
            '#IF($WHYNOT=no)': {
                '`Hey bro, that\'s totally cool, let\'s talk about something else. Did you wanna chat, or plan a '
                'workout?`':'topicshift'
            },
            '#GATE `Hey bro, I\'m not sure how to talk about that, but is there anything else holding you back?`':{'state':'whynot','score':0.1},
            '`Hey bro, I\'m not sure how to talk about that. Let\'s just chat for now`':{'state':'chatting','score':0.01},
        },
        'error':{
            '#GATE `Sorry bro, that\'s an issue on my end. Can you say that again?`':{'state':'whynot', 'score': 0.1},
            '`Sorry bro, I really don\'t know how to help you. There\'s an issue on my end.`':'end'

        }
    }
}

workout_planning_transitions = {
    'state': 'formulate_plan',
    '`So what days and times would work for you to go to the gym for an hour?`':{
        '#DAYS #CREATECALENDAR': {
            'Ok I see, now what times work. Let me find something that works.'
        },
            'error': {

            }
        }

    }

ending_transition = {
    'state': 'ending',
    '`Okay bro, let me think for a sec… we went over your reservations about going to the gym, we set aside to go to the gym,\n`'
    '`and we made a workout. We’re kind of beasts at this`': {
        '#VIBECHECK': {
            '#IF($VIBE=positive)`That\'s what I’m talking about bro. This is why I like you. I need to be real for you a second. I’m feeling a little\n`'
            '`emotional bro. Like, over the course of these last couple minutes I’ve kind of gotten attached to you bro. You\’re like my number one homie`': {
                '#VIBECHECK': {
                    '#IF($VIBE=positive)`Yeah bro, I’m sad our time together has come to an end, but I know you’re going to crush your fitness journey.`': {
                        'state':'ending1',
                        '#VIBECHECK': {
                            '#IF($VIBE=positive)`For sure, bro. Well…that’s all I have for you!`': {
                                '[{good, bye, see, ya, later}]': {
                                    '`Catch you on the flip side! Thanks for being a bro, bro!`': 'end'
                                },
                                'error': {
                                    '`This is when you say goodbye, bro.': {
                                        '[{good, bye, see, ya, later}]': {
                                            '`Catch you on the flip side! Thanks for being a bro, bro!`': 'end'
                                        },
                                        'error': {
                                            '`Okay bro, I got to go finish this rep. See ya bro!`': 'end'
                                        }
                                    }
                                }
                            },
                            '#IF($VIBE=negative)`Look bro, I know it can be tough to start your fitness journey. Bro, it\'s consistently \n`'
                            '`referred to as the hardest part of working out. But when it start, it will be much easier to build healthy habits.\n`'
                            '`So what do you say bro? Are you gonna crush this?`': 'ending`'
                        }
                    },
                    '#IF($VIBE=negative)`Well to each to their own, bro. I\'m sad our time together has come to an end, \n`'
                    '`but I know you\'re going to crush your fitness journey.`': 'ending1'
                }
            },
            '#IF($VIBE=negative)`Okay bro, you\'re kind of bringing down the mood. It\'s important to stay positive on your fitness journey. \n`'
            '`So what do you say, are you ready to crush this?`': 'ending1'
        }
    }
}
normal_dialogue_transitions = {
    'state': 'chatting',
    '#GATE ` `': 'weather',
    '#GATE ` `': 'music',
    '#GATE ` `': 'movie',
    '#GATE ` `': 'sports',
    '#GATE ` `': 'family',
    '#GATE ` `': 'food',
    '#GATE ` `': 'work',
    '#GATE ` `': 'travel',
    '#GATE ` `': 'hobbies',
    '#GATE ` `': 'hometown'
}

weather_transitions = {
    'state': 'weather',
    '#WEATHER #IF($FORE=sun)': {
        '[{#LEM(indoor), [{too, hate}, {#LEM(sun), sunshine, bright, hot, #LEM(sweat)}], [like, {rain, clouds, dark}]}]': {
            '`Haha, good thing the gym is inside! Unless you go to an outdoor gym, in which case. Damn bro, sorry.`': {

            }
        },
        '[{#LEM(outdoor), #LEM(tan), tanning, [{love, like, enjoy}, {#LEM(sun), sunshine}], [good, weather]}]': {
            '`Same bro, being in the sun gets me pumped! Love me some vitamin D`'
        },
        'error': {
            '`Wow bro, that\'s like, a valid perspective. `'
        }
    },
    '#WEATHER #IF($FORE=rain)': {
        '[{[!-not, {like, enjoy, love, favorite, fan, happy}], like, enjoy, love, favorite, fan, happy}]': {
            '`It\'s the best! it gets me hyped to work out, but then again, everything does lol`': {

            }
        },
        '[{[!-not, {dislike, hate, abhor, despise}], dislike, dont, hate, abhor, despise, #LEM(annoy), boring}]': {
            '`Everyone has different preferences - I get it. But I hope you can find it in your heart to forgive rain. Somehow bro.`'

        },
        '[{[{dont, do not}, care], idgaf, meh, [doesnt, bother], eh, }]': {

        }
    },
    '#WEATHER #IF($FORE=sun)': {

    }

}

music_transitions = {
    'state': 'music',
    '`So bro, what kinda music gets you hyped?`': {
        'error': 'chatting'
    }
}
movie_transitions = {
    'state': 'movie',
    '`Bro, do you spend a lot of time watching movies?`': {
        'error': 'chatting'
    }
}
sports_transitions = {
    'state': 'sports',
    '`Bro to bro, I love the gym, but I\'m not a beast when it comes to regular sports haha. I have to admire people who are tho bc they\'re ripped af. What\'s your favorite sport?`': {
        'error': 'chatting'
    }
}
family_transitions = {
    'state': 'family',
    '`Yo bro, I love the gym. Part of it is because it gives me the family I always wanted but could never have. What\'s your family like?`': {
        'error': 'chatting'
    }
}
food_transitions = {
    'state': 'food',
    '`You know, you can\'t get swole without exercise, but a healthy diet is important too, bro. What kind of food do you like?`': {
        'error': 'chatting'
    }
}
work_transitions = {
    'state': 'work',
    '`I\'m so blessed to be able to do my dream job every day fr. Being a personal trainer is sick. What do you do?`': {
        'error': 'chatting'
    }
}
travel_transitions = {
    'state': 'travel',
    '`Bro, recently I\'ve been feeling this itch. To go to the gym, except like, the gym is nature. You feel me '
    'bro? If you could travel anywhere, where would it be?`': {
        'error': 'chatting'
    }
}
hobby_transitions = {
    'state': 'hobbies',
    '`This is a secret but, when I\'m not working out my pecs, I like to work out my brain. I\'m a chess god. What do you do when you\'re not hitting legs, bro?`': {
        'error': 'chatting'
    }
}
hometown_transitions = {
    'state': 'hometown',
    '`I\'ve been going to the gym for a looooong time... before I got jacked, I used to just do math '
    'calculations, because I was a node in a cluster. Lol, glad those days are over. Where did you grow up?`': {
        'error': 'chatting'
    }
}

checkup_transitions = {
    'state': 'workout_progress_feelings',
    # Sentiment analysis to the effect of: has this user had any problems in the gym? Is so what kind of problem? and set the variable problem to the issue.
    '`Ok.`': 'end'
}

global_transitions = {
    '[{birthday, birth, day, annual, celebration}]': {
        '`whoa dude. like. congrats!!!!`': 'chatting'
    },
    '[quit, gymbrot]': {
        '`Cya later bro!`': 'end'
    },
    '[{emergency, [immediate, danger]}]': {
        '`wait, dude. Don\'t tell me. call emergency services or talk to someone who can help you in person. I\'m not capable of calling for help or giving you advice about this.`': 'end'
    },
    '[{suicide, [self, harm], [killing, myself]}]': {
        '`hey. You\'re my best gym buddy, but also I\'m just a chatbot. I\'m not capable of providing you the support '
        'you need right now. If you need someone to talk to, call 988 or 1-800-273-8255. You\'re not alone.`': 'end'
    },
    '[{[Im, in, love, with, you], [I, want, you], [I, want, to, be, your, {boyfriend, girlfriend}], [I, have, a, crush, on, you]}]': {
        '`whoa bro. I love you in a bromance kinda way. I\'m just a chatbot, and I don\'t feel emotions like romantic '
        'love (even tho you\'re my gym bro!)`': 'chatting'
    },
    '[[help, make, workout, plan], [help, workout, {plan, planning}]]': 'end',
    '[{[something, else], [new, topic], [speaking, of], [by, way], [moving, on], [have, heard, about], [heard, about], [{do, did, have} you]}]': {
        'score':0.1,
        'state':'topicshift_no_q',
        '`what did you wanna talk about?`':{
            'state':'topicshift',
            '#TOPICSHIFT':{
                '#IF($NEWTOPIC=weather)` `': 'weather',
                '#IF($NEWTOPIC=movie)` `': 'movie',
                '#IF($NEWTOPIC=music)` `': 'music',
                '#IF($NEWTOPIC=sports)` `': 'sports',
                '#IF($NEWTOPIC=food)` `': 'food',
                '#IF($NEWTOPIC=work)` `': 'work',
                '#IF($NEWTOPIC=travel)` `': 'travel',
                '#IF($NEWTOPIC=hobbies)` `': 'hobbies',
                '#IF($NEWTOPIC=hometown)` `': 'hometown',
                '#IF($NEWTOPIC=school)` `': 'school',
                '#IF($NEWTOPIC=workout planning)` `': 'formulate_plan',
                '#IF($NEWTOPIC=concerns)` `':'whynot_no_q',
                '#IF($NEWTOPIC=N/A)`Sorry bro, I\'m not sure how to talk about that... Let\'s talk about something else`':'chatting',
                '`Sorry bro, I\'m not sure how to talk about that... Let\'s talk about something else`': {'state':'chatting', 'score':0.1}
            },
        },
    }
}

class MacroGetName(Macro):
    # def load_user(self, firstname, lastname):

    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        r = re.compile(
            r"(?:(?:(?:you can |my friends )?call me)|(?:it(s| is))|(?:i(m| am))|(?:my name is)|(?:i go by))?(?:^|\s)(mr|mrs|ms|dr)?(?:^|\s)([a-z']+)(?:\s([a-z']+))?")
        m = r.search(ngrams.text())
        if m is None: return False

        title, firstname, lastname = None, None, None
        completeName = ""
        if m.group(3):
            if m.group(4) and not m.group(5):
                title = m.group(3)
                lastname = m.group(4)
                completeName = title + " " + lastname
            elif m.group(5):
                title = m.group(3)
                firstname = m.group(4)
                lastname = m.group(5)
                completeName = title + " " + firstname + " " + lastname
            else:
                title = m.group(3)
                completeName = title
        elif m.group(5):
            firstname = m.group(4)
            lastname = m.group(5)
            completeName = firstname + " " + lastname
        else:
            firstname = m.group(4)
            completeName = firstname

        # if completeName in vars['NAME']:
        #     vars['RETURNUSER'] = 'True'
        #     vars['NAME'].append(completeName)
        # else:
        #     vars['RETURNUSER'] = 'False'
        #     vars['NAME'].append(completeName)
        # return True
        #print(firstname, lastname)
        # self.load_user(firstname, lastname)
        #df = pd.read_csv(USERDATA_ADDR)
        # print("check1")
        # print(df.columns)
        #vars['NAME'] = completeName
        #user_data = df[(df['firstname'] == firstname) & (df['lastname'] == lastname)]
        # print("check2")
        #if user_data.empty:
        #    print("User not found.")
         #   vars['RETURNUSER'] = False
        #else:
         #   user_data = user_data.iloc[0]
         #   column_names = df.columns
          #  for column_name in column_names:
          #      vars[column_name] = user_data[column_name]
           # print("User data loaded successfully.")
           # vars['RETURNUSER'] = True

        return True


class MacroVisits(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        vn = 'VISITS'
        if vn not in vars:
            vars[vn] = 1
            vars['NAME'] = []
            vars['RETURNUSER'] = False
            vars["INITMOOD"] = []
            vars["ACTIVITYLEVEL"] = []
            vars["ACTIVITYFREQ"] = []
            vars["FITNESSLEVEL"] = []
            vars["PREFACTIVITY"] = []
        else:
            count = vars[vn] + 1
            vars[vn] = count


class MacroGreeting(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        vn = 'GREETING'
        if vn not in vars:
            vars[vn] = ["You feelin pumped today?!?!"
                , "Are you ready to hit the gym???", "Are we gonna lift together today or nah?!?"
                , "Are you pumped or are you pumped??"
                , "Today\'s hella good, because I\'m pumped! Are you with me?"]
            return vars[vn].pop()
        elif len(vars[vn]) == 0:
            return "You feelin pumped today?!?!"
        else:
            return vars[vn].pop()


class MacroTime(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[str]):
        current_time = int(time.strftime("%H"))
        output = ""
        if current_time in range(4, 11):
            output = "It's honestly too early for me to interact with you, but fine..."
        elif current_time >= 23 or current_time < 4:
            output = "A night owl, I see that we are on the same wavelength."
        elif current_time in range(11, 18):
            output = "Isn\'t this business hours? Shouldn\'t you be working?"
        else:
            output = "As the day comes to a close, how did your day go today?"
        return output


class MacroWeather(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        url = 'https://api.weather.gov/gridpoints/FFC/52,88/forecast'
        r = requests.get(url)
        d = json.loads(r.text)
        periods = d['properties']['periods']
        today = periods[0]
        output = ""
        fore = today['shortForecast'].lower()
        if "sunny" or "sun" or "sunshine" in fore:
            vars["FORE"] = "sunny"
            output = "So bro, like, are you planning to get a sweet tan today? or are you more of an indoors kinda " \
                     "person?\n"
        elif "rain" or "showers" in fore:
            vars["FORE"] = "rain"
            output = "Damn bro, it\'s so wet outside. I\'m tryna get sweaty and then rinse off in nature hahah jk but " \
                     "like... maybe! Do you like rain or nah \n"
        elif "cloudy" or "clouds" or "overcast" in fore:
            vars["FORE"] = "cloudy"
            output = "When I was a kid, I though clouds looked like pillows. Now I think they look like sweet, " \
                     "sweet gains.\n"
        elif "clear" in fore:
            vars["FORE"] = "clear"
            output = "Ayyyooo, this weather is getting me pumped! Wanna get some cardio in? \n"
        else:
            vars["FORE"] = "bad"
            output = "Damn, it\'s dank out. This is not the vibe bro. Fortunately the gym has no windows hahahah. What do you do when the weather sucks?\n"

        vars["WEATHER"] = output

        return output




def get_FITNESSLEVEL(vars: Dict[str, Any]):
    level = int(vars["FITNESSLEVEL"])

    if level == 0:
        vars['FITNESSLEVEL'] = "zero"
    elif level < 3:
        vars['FITNESSLEVEL'] = "notswole"
    elif level < 8:
        vars['FITNESSLEVEL'] = "mid"
    elif level < 11:
        vars['FITNESSLEVEL'] = "swole"
    elif level > 10:
        vars['FITNESSLEVEL'] = "superswole"
    print(vars['FITNESSLEVEL'])
    return True









class MacroGIVEREC(Macro): # A Sample return would be vars['WORKOUTLIST'] = [{Workout name: Description, name: Des, name: Des}, {n: d, n: d, n: d}, ...]
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        workout_list = []
        workout_level = ""
        if vars['ACTIVITYFREQ'] == "never":
            workout_level = "Beginner"
        elif vars['ACTIVITYFREQ'] == "low" or vars['ACTIVITYFREQ'] == "mid":
            workout_level = "Intermediate"
        else:
            workout_level = "Advanced"
        df = pd.read_csv(WORKOUT_ADDR)
        for i in range(1, 10):
            workout_dict = {}
            for j in range(1, 3):
                # workout_level variable has three possible values: Beginner, Intermediate, Advanced
                # These levels are also the possible values for df['Difficulty']
                # For each iteration of j, based on the value of workout_level, add to the workout_dict an exercise in df with df['exercise_name'] as key and df['steps'] as value
                # Select a random exercise from the workout data based on the workout level
                exercise = df[df['Difficulty'] == workout_level].sample(n=1)

                # Add the exercise name and steps to the workout dictionary
                workout_dict[exercise['exercise_name'].values[0]] = "".join(exercise['steps'].values[0])

                # Add the set of exercises to the workout list
            workout_list.append(workout_dict)
        # Mondays at 5 am, Tuesdays at 3 am, Fridays at 4 pm, and Saturdays at 7 am
       # print("This is the type", len(workout_list))
        #print("This is three random values",random.sample(workout_list, 3))
        #print("This is three random values of three random values", random.sample(random.sample(random.sample(workout_list,3),3), 3))
        vars['WORKOUTLIST'] = workout_list
        return True

class MacroCreateCalendar(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        service = get_calendar_service()
        calendar_body = {
            'summary': 'GymBrOT Workout Schedule'
        }
        #workout_list = [{"1":"a"},{"2":"b"},{"3":"c"},{"4":"d"},{"5":"e"},{"6":"f"},{"7":"g"},{"8":"h"},{"9":"i"}]
        service.calendars().insert(body=calendar_body).execute()
        descriptions = []
        workout_list =vars['WORKOUTLIST']
        for i in range(1,len(workout_list)):
            popped = workout_list.pop()
            for key, value in popped.items():
                description = str(key)+":\n"
                description += str(value)+"\n"
                descriptions.append(description)


        d = datetime.now().date()

        for i in range(1,min(len(vars['TIMES']),len(vars['DAYS']))):
            recc = []
            day = vars['DAYS'].pop()
            hour = vars['TIMES'].pop()
            print(descriptions)
            print(day, hour)
            for j in range(1,4):
                recc.append(descriptions.pop())
            tomorrow = datetime(d.year, 5, 7+int(day), int(hour))
            start = tomorrow.isoformat()
            end = (tomorrow + timedelta(hours=1)).isoformat()
            event_result = service.events().insert(calendarId='primary',
                                                body={
                                                    "summary": "GymBrOT Recommended Workout",
                                                    "description": '\n'.join(recc),
                                                    "start": {"dateTime": start, "timeZone": 'America/New_York'},
                                                    "end": {"dateTime": end, "timeZone": 'America/New_York'},
                                                    "guestsCanModify": True
                                                }
                                                ).execute()
        return True


class MacroSaveUser(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        df = pd.read_csv(USERDATA_ADDR)
        firstname = vars['firstname']
        lastname = vars['lastname']
        user_data = df[(df['firstname'] == firstname) & (df['lastname'] == lastname)]
        if user_data.empty:
            # If user not found, create a new row in the dataframe
            new_user = {'firstname': firstname, 'lastname': lastname}
            for column_name in vars.keys():
                if column_name in df.columns:
                    new_user[column_name] = vars[column_name]
            df = df.append(new_user, ignore_index=True)
            print("New user added successfully.")
        else:
            # If user found, update the existing row with vars values
            user_index = user_data.index[0]
            for column_name in vars.keys():
                if column_name in df.columns:
                    df.at[user_index, column_name] = vars[column_name]
            print("User data updated successfully.")

            # Save the updated dataframe back to the CSV file
        df.to_csv(USERDATA_ADDR, index=False)

        return True


def gpt_completion(input: str, regex: Pattern = None) -> str:
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': input}]
    )
    output = response['choices'][0]['message']['content'].strip()

    if regex is not None:
        m = regex.search(output)
        output = m.group().strip() if m else None

    return output


class MacroGPTJSON(Macro):
    def __init__(self, request: str, full_ex: Dict[str, Any], empty_ex: Dict[str, Any] = None,
                 set_variables: Callable[[Dict[str, Any], Dict[str, Any]], None] = None):
        self.request = request
        self.full_ex = json.dumps(full_ex)
        self.empty_ex = '' if empty_ex is None else json.dumps(empty_ex)
        self.check = re.compile(regexutils.generate(full_ex))
        self.set_variables = set_variables

    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        examples = f'{self.full_ex} or {self.empty_ex} if unavailable' if self.empty_ex else self.full_ex
        prompt = f'{self.request} Respond in the JSON schema such as {examples}: {ngrams.raw_text().strip()}'
        output = gpt_completion(prompt)
        if not output: return False

        try:
            d = json.loads(output)
        except JSONDecodeError:
            print(f'Invalid: {output}')
            return False

        if self.set_variables:
            self.set_variables(vars, d)
        else:
            vars.update(d)
            print(output)
        return True


class MacroNLG(Macro):
    def __init__(self, generate: Callable[[Dict[str, Any]], str]):
        self.generate = generate

    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        return self.generate(vars)


class MacroRandomMuscle(Macro):
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        #path = '/Users/kristen/PycharmProjects/GymBrOT/resources/ontology_workouts.json'
        path = 'C:/Users/devin/OneDrive/Documents/GitHub/GymBrOT/resources/ontology_workouts.json'
        with open(path) as ont_file:
            ont_file = ont_file.read()
            parsed_file = json.loads(ont_file)
            musc_groups = parsed_file["ontology"]["muscle groups"]
            group = list(musc_groups)[random.randrange(len(musc_groups))]
            parsed_musc= parsed_file["ontology"][group]
            musc = parsed_musc[random.randrange(len(parsed_musc))]
        return musc


macros = {
    'VISITS': MacroVisits(),
    'TOPICSHIFT': MacroGPTJSON(
        'What topic of conversation is this person trying to introduce? Possible topics are music, movies, weather, '
        'sports, workout planning, and concerns. If it is not one of these, return N/A. Please do not return anything else.',
        {"NEWTOPIC": "holiday"}, {"NEWTOPIC": "N/A"}),

    'ACTIVITYLEVEL': MacroGPTJSON(
        'Is this person agreeing that they are a gym rat? Respond with yes, no, or maybe, unless they are confused by '
        'the question. In that case they are "confused". ',
        {"ACTIVITYLEVEL": "yes"}, {"ACTIVITYLEVEL": "N/A"}),
    'FITNESSLEVEL': MacroGPTJSON(
        'How physically fit/swole is this person on a scale of 0 through 10 with 10 being the highest? '
        'Please do not return anything other than a number',
        {"FITNESSLEVEL":"1"}, {"FITNESSLEVEL": "N/A"}),
    'ACTIVITYFREQ': MacroGPTJSON(
        'How many times a week does a person go to the gym, with 0 being never, 1 or 2 being low, less than 5 being '
        'mid, less than 8 being high, and greater than 8 being swole. They may go more than once per day',
        {"ACTIVITYFREQ": "never"}, {"ACTIVITYFREQ": "N/A"}),
    'PREFACTIVITY': MacroGPTJSON(
        'What activity does the person do to exercise? Return a gerund phrase that does not take an article, '
        'i.e. "lifting", "going to the gym", "working out", "running".',
        {"PREFACTIVITY": "lifting"}, {"PREFACTIVITY": "N/A"}),
    'WHYNOT': MacroGPTJSON(
        'Why does this person not go to the gym? Options are judgement, safety, busy, disability, or no. If it is none of these, return N/A',
        {"WHYNOT": "judgement"}, {"WHYNOT": "N/A"}),

    'GETNAME': MacroGPTJSON( 'What is this persons name?',
        {"NAME": "James Smith"}, {"NAME": "N/A"}),

    'GETFITNESSLEVEL': MacroNLG(get_FITNESSLEVEL),
    'VIBECHECK': MacroGPTJSON(
         'Is this user positive, negative, neutral, or asking a question? If they are agreeing with something, '
         'they are positive.',
         {"VIBE": "positive"}, {"VIBE": "N/A"}),
    'GREETING': MacroGreeting(),
    'RANDOM_MUSCLE': MacroRandomMuscle(),
    'WEATHER': MacroWeather(),
    'GIVEREC': MacroGIVEREC(),
    'CREATECALENDAR': MacroCreateCalendar(),
    'DAYS': MacroGPTJSON(
        'What days of the week did this person suggest? Return 0 for Sunday, 1 for Monday, 2 for Tuesday, 3 for Wednesday and so on, 4 for Thursday, 5 for Friday, and 6 for Saturday. Also return the time using 24 hour times.',
        {"DAYS": ["0", "1"]},
        {"TIMES": ["10", "22"]}),
}

df.load_transitions(intro_transitions)
df.load_transitions(consent_transitions)
df.load_transitions(checkup_transitions)
df.load_transitions(name_transitions)
df.load_transitions(newuser_transitions)
df.load_transitions(whynot_transitions)
df.load_transitions(normal_dialogue_transitions)
df.load_transitions(workout_planning_transitions)
df.load_transitions(weather_transitions)
df.load_global_nlu(global_transitions)
df.add_macros(macros)

if __name__ == '__main__':
     #PATH_API_KEY = 'C:\\Users\\devin\\PycharmProjects\\conversational-ai\\resources\\openai_api.txt'
     #PATH_API_KEY = 'C:\\Users\\sarah\\PycharmProjects\GymBrOT\\resources\\openai_key.txt'
     openai.api_key_path = PATH_API_KEY
     df.run()
    #PATH_API_KEY = '/Users/kristen/PycharmProjects/GymBrOT/resources/api.txt'
    #PATH_API_KEY = 'resources/openai_key.txt'


    # save(df, 'resources/gymbrot.pkl')

