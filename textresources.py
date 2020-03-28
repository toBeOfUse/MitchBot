import random
import re


# creates a generator that yields the elements of the input list in a random order infinitely without repeating except
# when the list runs out
def choice_no_repeats(in_list):
    count = 0
    r = list(in_list)
    random.shuffle(r)
    while True:
        yield r[count]
        count += 1
        if count == len(r):
            count = 0
            random.shuffle(r)


poetry = \
    [
'''A gold-feathered bird
Sings in the palm, without human meaning
Without human feeling, a foreign song.''',
'''To drift with every passion till my soul
Is a stringed lute on which all winds can play
Is it for this that I have given away
Mine ancient wisdom, and austere control?''',
'''I have looked down the saddest city lane
I have passed by the watchman on his beat
And dropped my eyes, unwilling to explain.''',
'''I am sister to the rain;
Fey and sudden and unholy,
Petulant at the windowpane,
Quickly lost, remembered slowly.''',
'''I saw a man pursuing the horizon;
Round and round they sped.
I was disturbed at this;   
I accosted the man.
“It is futile,” I said,
“You can never —”

“You lie,” he cried,   
And ran on.''',
'''A Book of Verses underneath the Bough,
A Jug of Wine, a Loaf of Bread — and Thou
Beside me singing in the Wilderness —
Oh, Wilderness were Paradise enow!''',
'They picked out stones that hadn’t been worn completely round and threw them out into the water to make them rounder.',
'I just wish that you had made it beyond the bounds of this cold little radius, that when the archaeologists brush off this layer of our world in a million years and string off the boundaries of our rooms and tag and number every plate and table leg and shinbone, you would not be there',
'One prefers, of course, on all occasions to be stainless and above reproach, but, failing that, the next best thing is unquestionably to have got rid of the body',
"One of God's own prototypes. A high-powered mutant of some kind never even considered for mass production. Too weird to live, and too rare to die.",
"Once is happenstance; twice is coincidence; three times is enemy action.",
"Stealing is not excusable if, for instance, you are in a museum and you decide that a certain painting would look better in your house, and you simply grab the painting and take it there. But if you were very, very hungry, and you had no way of obtaining money, it might be excusable to grab the painting, take it to your house, and eat it.",
'conflict in stories is the poor writer\'s substitute for "the moon explodes and beloved makeout aliens come out"',
"It is much harder to forget music than to remember it. Paul Valéry, in his guise of Monsieur Teste, claimed that he had a system for recalling everything he wanted to know but had never found a way to forget what he preferred not to remember.",
"Myself, I've never found a host and hostess who could stick my presence for more than about a week. Indeed, long before that as a general rule the conversation at the dinner table is apt to turn on the subject of how good the train service to London is, those present obviously hoping wistfully that Bertram will avail himself of it. Not to mention the time-tables left in your room with a large cross against the 2.35 and the legend “Excellent train. Highly recommended.”",
"The aged Devil sat on a rock by the side of a Finnish country road. The Devil was ten thousand, maybe twenty thousand years old, and very tired. He was covered in dust. His whiskers were wilting. Whither be ye gang in sich ’aste? the Devil called out to a Farmer. Done broke me ploughshare and must to fixe it, the Farmer replied. Not to hurrie, said the Devil, the sunne still play es o’erhead on highe, wherefore be ye scurrying? Sit ye doun and ‘eare m’ tale. The Farmer knew no good could come of passing time with the Devil, but seeing him so utterly haggard, the Farmer-",
"“It’s funny about love,” Sophia said. “The more you love someone, the less they like you back.” “That’s very true,” Grandmother observed. “And so what do you do?” “You go on loving,” said Sophia threateningly. “You love harder and harder.” Her grandmother sighed and said nothing.",
'''(If you have ever quit an imaginary job over an imaginary paycut,
mistakenly taken your house's thermostat for a dial with which to focus the windows,
written a play about the special relationship that blooms when a withdrawn honor student is assigned to tutor the school's basketball star,
been deafened by the panoply of voices in the classifieds
tied up every private detective in town with false leads,
taken photos of people saying "shut up,"
or know a place where you can get married at midnight,
then you know what I'm talking about.)''',
"Live ♡ Laugh ♡ Love",
"Wherein differ the sea and the land, that a miracle upon one is not a miracle upon the other?",
'''Come, every frustum longs to be a cone,
And every vector dreams of matrices.
Hark to the gentle gradient of the breeze:
It whispers of a more ergodic zone.

In Riemann, Hilbert or in Banach space
Let superscripts and subscripts go their ways
Our asymptotes no longer out of phase,
We shall encounter, counting, face to face.

I'll grant thee random access to my heart,
Thou'lt tell me all the constants of thy love;
And so we two shall all love's lemmas prove,
And in our bound partition never part.''',
"Good boy you! Black Labrador",
"Whatever you now find weird, ugly, uncomfortable and nasty about a new medium will surely become its signature. CD distortion, the jitteriness of digital video, the crap sound of 8-bit—all of these will be cherished and emulated as soon as they can be avoided.... The distorted guitar sound is the sound of something too loud for the medium supposed to carry it. The blues singer with the cracked voice is the sound of an emotional cry too powerful for the throat that releases it.",
"Hey baby, are you a shallow grave? Because I figure that's where they'll find my body",
"the interesting and paradoxical thing about Dionysos is that this historically ancient god is perennially depicted as newly arriving everywhere he goes. in other words he is a god of beginnings: when you first start to fall in love or get drunk or have an idea—that is the intoxication called Dionysos, new every time.",
'''“Oh, help!” said Pooh, as he dropped ten feet on the branch below him.
“If only I hadn’t—” he said, as he bounced twenty feet on to the next branch.
“You see, what I meant to do,” he explained, as he turned head-over-heels, and crashed on to another branch thirty feet below, “what I meant to do—”
“Of course, it was rather—” he admitted, as he slithered very quickly through the next six branches.
“It all comes, I suppose,” he decided, as he said goodbye to the last branch, spun round three times, and flew gracefully into a gorse-bush, “it all comes of liking honey so much. Oh, help!”''',
'''Tyger Tyger, burning bright, 
In the forests of the night; 
What immortal hand or eye, 
Could frame thy fearful symmetry?

In what distant deeps or skies
Burnt the fire of thine eyes?
On what wings dare he aspire?
What the hand, dare seize the fire?''',
"Ninety per cent of most magic merely consists of knowing one extra fact.",
"Inexperienced travellers might think that 'Aargh!' is universal, but in Betrobi it means 'highly enjoyable' and in Howondaland it means, variously, 'I would like to eat your foot', 'Your wife is a big hippo' and 'Hello, Thinks Mr Purple Cat.' One particular tribe has a fearsome reputation for cruelty merely because prisoners appear, to them, to be shouting 'Quick! Extra boiling oil!'",
'''We have all seized the white perimeter as our own
and reached for a pen if only to show
we did not just laze in an armchair turning pages;
we pressed a thought into the wayside,
planted an impression along the verge.

Even Irish monks in their cold scriptoria
jotted along the borders of the Gospels
brief asides about the pains of copying,
a bird singing near their window,
or the sunlight that illuminated their page-
anonymous men catching a ride into the future
on a vessel more lasting than themselves.''',
'''                          A world of made
is not a world of born --- pity poor flesh

and trees, poor stars and stones, but never this
fine specimen of hypermagical

ultraomnipotence. We doctors know

a hopeless case if --- listen: there's a hell
of a good universe next door; let's go''',
"But that, you see, my dear Kermit, would be altogether impossible. I could never be myself... You see, there is no me. I do not exist…! There used to be a me, but I had it surgically removed.",
"I give myself very good advice, but I very seldom follow it",
"It doesn't matter if the glass is half full or half empty. I am going to drink it through this crazy straw",
"“That’s another problem for another day,” the Golux said. “Time is for dragonflies and angels. The former live too little and the latter live too long.”",
"Hark began to chew again. “No mortal man can murder time,” he said, “and even if he could, there’s something else: a clockwork in a maiden’s heart, that strikes the hours of youth and love, and knows the southward swan from winter snow, and summer afternoons from tulip time.” “You sicken me with your chocolate chatter,” snarled the Duke. “Your tongue is made of candy.”",
"And she's got brains enough for two, which is the exact quantity the girl who marries you will need.",
"A melancholy-looking man, he had the appearance of one who has searched for the leak in life's gas-pipe with a lighted candle.",
"Zeppo came out from the wings and announced, ‘Dad, the garbage man is here.’ I replied, ‘Tell him we don’t want any.’",
"Never have I waltzed to \"My Country 'Tis Of Thee,\" nor met anyone who did. Still, it's a waltz, for it's written in waltz time.",
"The moral of Snow White is \"never eat apples.\""
    ]

poetry_generator = choice_no_repeats(poetry)

nicknames = ["Accidental Genius", "Ace", "Adorable", "Alpha", "Amazing", "Angel Eyes", "Angel Face", "Angel Heart",
             "Angelito", "Atom", "Autumn", "Azúcar", "Baba Ganoush", "Bad Kitty", "Bam Bam", "Bambi", "Beagle", "Bean",
             "Beanie", "Bear", "Bearded Genius", "Biggie", "Biscuit", "Bitsy", "Blister", "Blondie", "Blue Eyes",
             "Blueberry", "Book Worm", "Boss", "Bowie", "Bowler", "Brainiac", "Brave Heart", "Breadmaker",
             "Bright Eyes", "Bro", "Brown Eyes", "Buckeye", "Buckshot", "Buddy", "Bugger", "Buster", "Butcher",
             "Button", "Cabbie", "Cadillac", "Cakes", "Candy", "Captain", "Captain Peroxide", "Caramel", "Care Bear",
             "Caretaker", "Champ", "Chardonnay", "Charming", "Chef", "Chicago Blackout", "Chocolate Thunder", "Chubs",
             "Chuckles", "Cinnamon", "Claws", "Coco", "Commando", "Confessor", "Cookie", "Cool Whip", "Cosmo",
             "Crash Override", "Crash Test", "Crazy Eights", "Cream", "Cuddle Bear", "Cuddle Buddy", "Cuddle Bug",
             "Cuddle Bunny", "Cuddle Muffin", "Cuddly Bear", "Cuddly Wuddly", "Cupcakes", "Curls", "Cute Bunny",
             "Cute Pie", "Cuteness", "Cutesy Pie", "Cutie", "Cutie Boo", "Cutie Head", "Cutie Pants", "Cutie Patootie",
             "Cutie Pie", "Daddy", "Dancing Madman", "Dark Horse", "Darling", "Dashing", "Dear", "Dear Heart",
             "Dearest", "Dearest One", "Dearie", "Deep Water", "Destiny", "Dew Drop", "Diamond", "Dimples", "Dolce",
             "Dove", "Dragonfly", "Dream Boat", "Dream Guy", "Dream Lover", "Dreamer", "Dreamweaver", "Dreamy",
             "Duckling", "Eclipse", "Egghead", "Electric Player", "Elf", "Enigma", "Everything", "Eye Candy", "Fantasy",
             "Favorite", "Feisty", "Fine Wine", "Firecracker", "Firefly", "Flakes", "Flame", "Flash", "Flint", "Fluffy",
             "Foxy", "Freak", "Freckles", "Frostbite", "Frozen Fire", "Fruit Cake", "Fruit Loop", "Fun Size", "Gangsta",
             "Gas Man", "Gem", "Genie", "Genius", "Ghost", "Giggles", "Gold", "Good Looking", "Goody Goody", "Goof",
             "Goof Ball", "Goofy", "Google", "Gorgeous", "Grasshopper", "Grave Digger", "Green", "Grimm", "Guillotine",
             "Gumdrop", "Gummy Bear", "Gunhawk", "Happiness", "Happy Face", "Haven", "Heart & Soul", "Heart Stopper",
             "Heart Throb", "Heart’s Desire", "Heartbreaker", "Heartie", "Heaven Sent", "Hero", "Hightower", "Hobbit",
             "Hog Butcher", "Hollywood", "Honey", "Honey Bagel", "Honey Bear", "Honey Bee", "Honey Bird", "Honey Bun",
             "Honey Bunch", "Honey Bunny", "Honey Lips", "Honey Love", "Honey Muffin", "Honey Pie", "Honey Pot",
             "Honey Sugar Bumps", "Honeysuckle", "Hop", "Hot Cakes", "Hot Chocolate", "Hot Lips", "Hot Pants",
             "Hot Stuff", "Hotness", "Hotshot", "Hotsy-Totsy", "Hottie", "Hottie Tottie", "Houston", "Hubba Bubba",
             "Huggie", "Huggies", "Huggy Bear", "Hugster", "Hun", "Hyper", "Ivy", "Jazzy", "Jester", "Jewel", "Jigsaw",
             "Jockey", "Joker’s Grin", "Joy", "Judge", "K-9", "Keystone", "Khal", "Kickstart", "Kiddo", "Kill Switch",
             "Kingfisher", "Kissy Face", "Kit Kat", "Kitchen", "Kitten", "Kitty Cat", "Knockout", "Knuckles",
             "Lady Killer", "Lamb", "Lamb Chop", "Lambkin", "Lambkins", "Lapooheart", "Legs", "Lemon", "Life Mate",
             "Lifeline", "Light Priest", "Lightning Ball", "Lil Dove", "Lil One", "Lil’ Heart Breaker",
             "Liquid Science", "Little Bear", "Little Bit", "Little Bits", "Little Cobra", "Little Dove",
             "Little General", "Little Guy", "Little Lamb", "Little Puff", "Lollipop", "Looker", "Lord Nikon",
             "Lovatar", "Love", "Love Bear", "Love Boodle", "Love Bug", "Love Face", "Love Genie", "Love Lumps",
             "Love Muffin", "Love Nugget", "Lovebird", "Lover Boy", "Lover Doll", "Lucky", "Lucky Charm", "Luna",
             "Lunar", "Mad Jack", "Magic", "Magic Guy", "Magician", "Major", "Manimal", "Marbles", "Married Man",
             "Marshmallow", "Mellow", "Melody", "Mental", "Micro", "Mine", "Mini", "Mini Me", "Minion", "Minnie Mouse",
             "Misty Eyes", "Mon Amour", "Mon Coeur", "Monkey", "Mookie", "Mooky Porky", "Moon Beam", "Moonlight",
             "Moonshine", "Motherboard", "Mouse", "Movie Star", "Fabulous", "Gadget", "Lucky", "Peppermint", "Spy",
             "Thanksgiving", "Wholesome", "Muffin", "Munchies", "Munchkin", "Nacho", "Natural Mess", "Nibbles",
             "Night Train", "Nightmare King", "Nine", "Ninja", "Nugget", "Num Nums", "Nutty", "Odd Duck", "Omega",
             "One and Only", "Onion King", "Oreo", "Other Half", "Overrun", "Pancake", "Panda", "Panda Bear",
             "Papa Smurf", "Paradise", "Paramour", "Passion", "Passion Fruit", "Peach", "Peaches", "Peaches and Crème",
             "Peachy", "Peachy Pie", "Peanut", "Pearl", "Pebbles", "Perfect", "Pet", "Pickle", "Pickle Pie", "Pikachu",
             "Pineapple", "Pineapple Chunk", "Pint Size", "Pipsqueak", "Pluto", "Poker Face", "Pop Tart", "Precious",
             "Prince", "Prize", "Prometheus", "Psycho Thinker", "Pudding", "Pumpkin", "Pumpkin Pie", "Punk", "Puppy",
             "Pusher", "Quake", "Quirky", "Rabbit", "Radical", "Raindrop", "Rashes", "Ray", "Rebel", "Red",
             "Ride or Die", "Roadblock", "Rockstar", "Rooster", "Rug-Rat", "Rum-Rum", "Runner", "Saint", "Sandbox",
             "Santa Baby", "Scooter", "Scrapper", "Screwtape", "Scrumptious", "Serial Killer", "Sex Bomb", "Sex Kitten",
             "Sex Muffin", "Sexiness", "Sexual Chocolate", "Sexy", "Sexy Angel", "Sexy Bear", "Sexy Devil", "Sexy Dork",
             "Sexy Eyes", "Sexy Guy", "Sexy Pants", "Sexy Pie", "Shadow", "Shadow Chaser", "Share Bear",
             "Sherwood Gladiator", "Shining Star", "Shooter", "Short Stuff", "Shortcake", "Shorty", "Shot Glass",
             "Shrimpy", "Shug", "Shy", "Sidewalk Enforcer", "Silly Goose", "Skippy", "Skittles", "Skull Crusher", "Sky",
             "Sky Bully", "Slick", "Slicky", "Slow Trot", "Small Fry", "Smallie", "Smart Cookie", "Smarty", "Smiles",
             "Smiley", "Smiley Face", "Snake Eyes", "Snappy", "Snicker Doodle", "Snookums", "Snow Bunny", "Snow Hound",
             "Snow Pea", "Snowflake", "Snuggle Able", "Snuggle Bear", "Snuggles", "Snuka Bear", "Soda Pop", "Sofa King",
             "Soldier", "Soul Friend", "Soul Mate", "Spark", "Sparky", "Speedwell", "Sphinx", "Spiky", "Spirit",
             "Sport", "Spring", "Springheel Jack", "Sprinkles", "Squatch", "Squirrel", "Squishy", "Stacker of Wheat",
             "Star", "Star Bright", "Star Light", "Stepper", "Sugams", "Sugar", "Sugar Babe", "Sugar Bear",
             "Sugar Biscuit", "Sugar Boy", "Sugar Lips", "Sugar Man", "Sugar Pants", "Suicide Jockey", "Suitor",
             "Sunflower", "Sunshine", "Super Guy", "Super Man", "Super Star", "Swampmasher", "Sweet", "Sweet Baby",
             "Sweet Dream", "Sweet Heart", "Sweet Kitten", "Sweet Lips", "Sweet Love", "Sweet Lover", "Sweet One",
             "Sweet Tart", "Sweet Thang", "Sweetie", "Swerve", "Tacklebox", "Take Away", "Tarzan", "Tater Tot",
             "Tea Cup", "Teddy", "Teddy Bear", "Tender Heart", "Tesoro", "The China Wall", "Thrasher", "Tiger", "Tiggy",
             "Tiny Boo", "Toe", "Toolmaker", "Tough Guy", "Tough Nut", "Treasure", "Treasure Trove", "Tricky", "Trip",
             "True Love", "TumTums", "Turtle", "Turtle Dove", "Tweetie", "Tweetie-Pie", "Tweetums", "Twinkie",
             "Twinkle Toes", "Twitch", "Uber", "Ultimate", "Unicorn", "Unstoppable", "Untamed", "Vagabond Warrior",
             "Valentine", "Viking", "Vita", "Voluntary", "Vortex", "Waffles", "Washer", "Waylay Dave", "Wee-One",
             "Westie", "Wheels", "Wolfie", "Wonder Guy", "Wonder Man", "Wonderful", "Woo Bear", "Woo Woo", "Woody",
             "Wookie", "Wookums", "Wordsmith", "Wuggle Bear", "Wuggles", "Xoxo", "Yankee", "Young Guy", "Youngest",
             "Yummers", "Yummy", "Yummy Bear", "Zany", "Zesty Dragon", "Zod", "Abba Zabba", "Almond Joy", "Amorcita",
             "Angel", "Angel Baby", "Angel Face", "Angel Legs", "Angel Wing", "Angelita", "Aphrodite", "Babe", "Baby",
             "Baby Bear", "Baby Carrot", "Baby Doll", "Baby Girl", "Baby Love", "Baby Spice", "Babycakes", "Bambi",
             "Barbie", "Bean", "Bear", "Beautiful", "Beauty", "Bella", "Betty Boo", "Big Love", "Bite-size",
             "Bitty Love", "Blondie", "Blueberry Pie", "Bonita", "Boo", "Booboo", "Bookworm", "Booty Beauty", "Bossy",
             "Brownie", "Bubba", "Bubble Butt", "Bubble Gum", "Bubbles", "Buddy", "Bug", "Bugaboo", "Bugaloo",
             "Buggly Boo", "Bundt Cake", "Butter Butt", "Butter Tart", "Butterbomb", "Butterbutt", "Buttercup",
             "Butterfinger", "Butterfly", "Butterscotch", "Button", "Candy Cane", "Carmel", "Carmelita", "Carmella",
             "Cat woman", "Cheezit", "Cherubie", "Chicken Tender", "Chicken Wing", "Chiquitita", "Chubby Cheeks",
             "Chubs", "Cinderella", "Cinnabon", "Cinnamon", "Cookie", "Corn Nut", "Cowgirl", "Cracker Jack",
             "Crispie Treat", "Critter", "Cuddle Bug", "Cuddly Boop", "Cuddly Duddly", "Cupcake", "Curls", "Curly-Q",
             "Curvy", "Cute Boot", "Cute Bot", "Cuteness", "Cutie", "Cutie Bug", "Cutie Buggles", "Cutie Cuddles",
             "Cutie Patootie", "Cutie Pie", "Cutie Sniggles", "Cutie Snuggles", "Cutie Toes", "Cutie Wiggles", "Daisy",
             "Damsel", "Darling", "Dear", "Dearest", "Dibbles", "Dilly Dolly", "Dimples", "Doll face", "Dolly",
             "Dorito", "Double Bubble", "Double Love", "Double Stuff", "Double Trouble", "Dove", "Dovey Lovey",
             "Dream Girl", "Duchess", "Dum Dum", "Dumpling", "Ella", "Enchantress", "Fibbles", "Fillity Tuna",
             "Filly Billy", "Flame", "Foxy Lady", "French Fry", "Frito", "Funfetti", "Funion", "Fun-size", "Gaga",
             "Gibbles", "Giggles", "Glass of Sunshine", "Goal Baby", "Goddess", "Goldie", "Goldie Locks", "Goo Goo",
             "Goober", "Goody Bar", "Gorgeous", "Green Love", "Gribbles", "Gubble Bum", "Gumball", "Gumdrop",
             "Gummy Bear", "Gummy Worm", "Half Pint", "Heaven-Sent", "Hershey’s", "Honey", "Honey Buns", "Honey Butt",
             "Honey Loaf", "Honey Tots", "Honey Wiggles", "Honeymaid", "Honeypot", "Hot Bod", "Hot Butt", "Hot Cakes",
             "Hot Cross Buns", "Hot French Fry", "Hot Mama", "Hot Potato", "Hot Sauce", "Hot Tater Tot", "Hot Thing",
             "Hotlips", "Hottie Po-tottie", "Hurricane", "Icee Pop", "Ittle Skittle", "Itty Bitty Sugar Bomb", "Jammer",
             "Jazzie", "Jellie Belly", "Jelly Bean", "Jelly Belly", "Jelly Sweets", "Jellybean", "Jolly Rancher",
             "Juicy", "Juicy Fruity", "Juliet", "Junior Mint", "Khaki Lassie", "Kiddo", "Kit Kat", "Kitten", "Kitty",
             "Lady Bug", "Lady Godiva", "Laffy Taffy", "Lervey Dervy", "Libbles", "Lifesaver", "Lil Antoinette",
             "Lil Ma’am", "Lil Mama", "Lil Miss", "Lioness", "Lip Smacker", "Little Bear", "Little Love", "Little Mama",
             "Little Rascal", "Loca", "Lolita", "Lolli Lolli", "Lollipop", "Love", "Love Bud", "Love Muffin",
             "Love on Fire", "Lovebug", "Lover Girl", "Lovey", "Lovey Butt", "Lovey Dovey", "Lovey Tickles", "Luvski",
             "Luvvy Wuvvy", "M&M", "Mallow Cup", "Mama of Drama", "Mamacita", "Mami", "Maple Leaf", "Marshymallow",
             "Meow", "Mi Novia-citita", "Milk Dud", "Milly", "Mine", "Minnie", "Missy", "Misty May", "Momacita",
             "Monkey", "Monkey Toes", "Mooncake", "Mouse", "Muffin", "Muffin Butt", "Munchkin", "My Darling", "My Love",
             "My Lovely", "My Sunshine", "Names Inspired by Angels", "Nibbles", "Nutter Butter", "Okie", "Pancake",
             "Peaches", "Peach-o", "Peanut", "Pearly", "Pearls", "Pebbles", "Perf Perf", "Perky", "Pet", "Pickle",
             "Pink Starburst", "Pinky", "Pippy", "Pocket-size", "Pookie", "Pop Tart", "Precious", "Pretty",
             "Pretty Lady", "Pretty Love", "Princesa", "Princess", "Princess Peach", "Principessa", "Principessa",
             "Pudding", "Pumpkin", "Pumpkin Pie", "Punk", "Punkin", "Pussycat", "Quarter Note", "Queenie", "Raisenette",
             "Rapunzel", "Red-Hot Bon Bon", "Rocket Pop", "Rolo", "Rose", "Ruffle", "Runt", "Saddle", "Sassy Lassy",
             "Scarlet", "Secret Sauce", "Señorita", "Sex Enchantress", "Sex Witch", "Sexy Lady", "Sexy Mama",
             "She’s fun, isn’t she?", "Shortcake", "Shorty", "Sirena", "Sizzle Pop", "Skittle", "Skittles",
             "Sleeping Beauty", "Small Fry", "Smartie", "Smarty Pants", "Smiles", "Snack", "Snackems", "Snibbles",
             "Snickerdoodle", "Snickers", "Snizzle Snacks", "Snookie", "Snookums", "Snow White", "Snowflake",
             "Snuggle Bug", "Snuggle Wumps", "Snugglebear", "Snuggly Bear", "Splendi", "Sporty Spice", "Sprout",
             "Squirrel", "Squirt", "Steak Tip", "Sticky Bun", "Sugar", "Sugar Babe", "Sugar Bits", "Sugar Bomb",
             "Sugar Buns", "Sugar Lips", "Sugar Mama", "Sugar Mouse", "Sugar Nova", "Sugar Plum", "Sugar Sauce",
             "Sugar Sugar", "Sunshine", "Supergirl", "Sushi", "Sweet Bun", "Sweet Eclair", "Sweet Heart",
             "Sweet Honey Love", "Sweet Loaf", "Sweet Mama", "Sweet Melody", "Sweet Pea", "Sweet Peach", "Sweet Tart",
             "Sweet Thing", "Sweetie", "Sweetie Pie", "Sweets", "Swiss Roll", "Swizzle", "Swizzly Sue Thompkins",
             "Tagalong", "Tart", "Tastee Squeeze", "Tater Tot", "Teddy Graham", "Teehee", "Temptress", "Thin Mint",
             "Thumbelina", "Tibbles", "Tic Tac", "Tiffy Taffy", "Tigress", "Tilly", "Tinkerbell", "Tiny One",
             "Tippy Tappy", "Toffee", "Toffee Lolly", "Tooti", "Toots", "Tootsie", "Tootsie Roll", "Tostito",
             "Triple Love", "Triscuit", "Trolli", "Tuggles", "Tutta", "Tutti Frutti", "Tweety", "Twinkie", "Twinkle",
             "Twix", "Twizzle Top", "Twizzler", "Waffles", "Whirly Pop", "Whoopie Pie", "Whopper", "Wifey",
             "Wittle Wifey", "Wonder Girl", "Wonder Woman", "Wuggles", "Yummy"]


def cursive(text, keep_emojis=False):
    emoji_regex = r"(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])"
    cursive_dict = {"0": "𝟢", "1": "𝟣", "2": "𝟤", "3": "𝟥", "4": "𝟦", "5": "𝟧", "6": "𝟨", "7": "𝟩",
                    "8": "𝟪", "9": "𝟫", "a": "𝒶", "b": "𝒷", "c": "𝒸", "d": "𝒹", "e": "𝑒", "f": "𝒻",
                    "g": "𝑔", "h": "𝒽", "i": "𝒾", "j": "𝒿", "k": "𝓀", "l": "𝓁", "m": "𝓂", "n": "𝓃",
                    "o": "𝑜", "p": "𝓅", "q": "𝓆", "r": "𝓇", "s": "𝓈", "t": "𝓉", "u": "𝓊", "v": "𝓋",
                    "w": "𝓌", "x": "𝓍", "y": "𝓎", "z": "𝓏", "A": "𝒜", "B": "𝐵", "C": "𝒞", "D": "𝒟",
                    "E": "𝐸", "F": "𝐹", "G": "𝒢", "H": "𝐻", "I": "𝐼", "J": "𝒥", "K": "𝒦", "L": "𝐿",
                    "M": "𝑀", "N": "𝒩", "O": "𝒪", "P": "𝒫", "Q": "𝒬", "R": "𝑅", "S": "𝒮", "T": "𝒯",
                    "U": "𝒰", "V": "𝒱", "W": "𝒲", "X": "𝒳", "Y": "𝒴", "Z": "𝒵"}
    cursive_text = ''.join([(cursive_dict[x] if x in cursive_dict else x) for x in text.content])
    cleaned_cursive_text = re.sub(emoji_regex, ' ', cursive_text).strip() if not keep_emojis else cursive_text.strip()
    return cleaned_cursive_text
