import random
import re
import sqlite3
import json
from typing import Sequence

random_db = sqlite3.connect("db/random.db")


class RandomNoRepeats:
    """
    Class that wraps a sequence and returns a random item from it, repeating items
    only when every item in the sequence has already been used once and never
    returning the same item twice in a row. This class persists its state through the
    SQLite file db/random.db. Because the user may wish to change the contents of a
    specific sequence between program executions, sequences are uniquely identified
    by a string name rather than by their contents.
    """

    def __init__(self, source: Sequence, name: str):
        if len(source) < 2:
            assert("RandomNoRepeats object needs > 1 source items")
        self.source = list(source)
        self.name = name

        cur = random_db.cursor()
        cur.execute("create table if not exists random " +
                    "(name text primary key, used_items text)")
        cur.execute("create index if not exists by_name on random (name)")
        existing_row = cur.execute(
            "select used_items from random where name=?",
            (name,)).fetchone()
        if existing_row is not None:
            self.used_items = [x for x in json.loads(existing_row[0]) if x in source]
        else:
            self.used_items = []

    def save(self):
        cur = random_db.cursor()
        cur.execute("insert or replace into random " +
                    "(name, used_items) values (?, ?)",
                    (self.name, json.dumps(self.used_items)))
        random_db.commit()

    def get_item(self):
        """Returns a random element that has not been used unless absolutely necessary."""
        if len(self.used_items) >= len(self.source):
            self.used_items = self.used_items[-1:]
        item = random.choice(self.source)
        while item in self.used_items:
            item = random.choice(self.source)
        self.used_items.append(item)
        self.save()
        return item


def get_poetry_generator():
    with open("text/poetry.txt", encoding="utf-8") as poetry_file:
        raw_poems = poetry_file.read().split("\n---\n")
        poetry = [p.strip() for p in raw_poems if p.strip()]
    source = RandomNoRepeats(poetry, "poetry")
    while True:
        yield source.get_item()


poetry_generator = get_poetry_generator()

nicknames = [
    "Accidental Genius", "Ace", "Adorable", "Angel Face", "Angel Heart", "Angelito", "Baba Ganoush",
    "Bad Kitty", "Bam Bam", "Bambi", "Beagle", "Bean", "Biscuit", "Bitsy", "Blister", "Blondie",
    "Blue Eyes", "Blueberry", "Book Worm", "Bowler", "Brainiac", "Brave Heart", "Breadmaker",
    "Bright Eyes", "Bro", "Brown Eyes", "Buckeye", "Buckshot", "Buster", "Button", "Cadillac",
    "Cakes", "Captain Peroxide", "Caramel", "Care Bear", "Caretaker", "Champ", "Chardonnay",
    "Chicago Blackout", "Chocolate Thunder", "Chuckles", "Cinnamon", "Claws", "Commando", "Cookie",
    "Cool Whip", "Cosmo", "Crash Override", "Crash Test", "Crazy Eights", "Cream", "Cuddle Bear",
    "Cuddle Buddy", "Cuddle Bug", "Cuddle Bunny", "Cuddle Muffin", "Cuddly Bear", "Cuddly Wuddly",
    "Cupcakes", "Curls", "Cute Bunny", "Cutesy Pie", "Cutie Boo", "Cutie Head", "Cutie Pants",
    "Daddy", "Dancing Madman", "Dark Horse", "Dear Heart", "Dearest One", "Deep Water", "Dew Drop",
    "Dove", "Dragonfly", "Dream Boat", "Dream Guy", "Dream Lover", "Dreamweaver", "Duckling",
    "Eclipse", "Egghead", "Eye Candy", "Fine Wine", "Firecracker", "Firefly", "Fluffy", "Foxy",
    "Freckles", "Frostbite", "Frozen Fire", "Fruit Cake", "Fruit Loop", "Fun Size", "Gas Man",
    "Gem", "Genie", "Genius", "Ghost", "Giggles", "Good Looking", "Goody Goody", "Goof Ball",
    "Grasshopper", "Grave Digger", "Gumdrop", "Gummy Bear", "Gunhawk", "Happy Face", "Heart & Soul",
    "Heart Stopper", "Heart Throb", "Heart’s Desire", "Heartbreaker", "Heartie", "Heaven Sent",
    "Hightower", "Hollywood", "Honey Bagel", "Honey Bear", "Honey Bird", "Honey Bun", "Honey Bunch",
    "Honey Bunny", "Honey Muffin", "Honey Pie", "Honey Pot", "Honey Sugar Bumps", "Hot Cakes",
    "Hot Chocolate", "Hotshot", "Hotsy-Totsy", "Hottie Tottie", "Houston", "Hubba Bubba",
    "Huggy Bear", "Hugster", "Jazzy", "Jester", "Jewel", "Joker’s Grin", "Keystone", "Khal",
    "Kill Switch", "Kingfisher", "Kissy Face", "Kit Kat", "Knockout", "Knuckles", "Lamb Chop",
    "Lemon", "Lifeline", "Light Priest", "Lightning Ball", "Li'l Dove", "Li'l One",
    "Liquid Science", "Little Bear", "Little Cobra", "Little Dove", "Little General", "Little Guy",
    "Little Lamb", "Little Puff", "Lord Nikon", "Lovatar", "Love Boodle", "Love Bug", "Love Genie",
    "Love Nugget", "Lovebird", "Lover Boy", "Lover Doll", "Lucky Charm", "Mad Jack", "Magic Guy",
    "Marbles", "Married Man", "Marshmallow", "Mini Me", "Minnie Mouse", "Misty Eyes", "Mon Amour",
    "Mooky Porky", "Moon Beam", "Moonlight", "Moonshine", "Motherboard", "Movie Star", "Munchkin",
    "Nacho", "Natural Mess", "Nibbles", "Night Train", "Nightmare King", "Nugget", "Odd Duck",
    "One and Only", "Onion King", "Oreo", "Other Half", "Pancake", "Panda Bear", "Papa Smurf",
    "Passion Fruit", "Peaches and Crème", "Peachy Pie", "Pebbles", "Pickle Pie", "Pikachu",
    "Pineapple Chunk", "Poker Face", "Pop Tart", "Prometheus", "Radical", "Raindrop", "Ride or Die",
    "Roadblock", "Rockstar", "Rooster", "Rug-Rat", "Santa Baby", "Scooter", "Scrapper", "Screwtape",
    "Sexy Pie", "Shadow Chaser", "Share Bear", "Sherwood Gladiator", "Shining Star", "Shooter",
    "Short Stuff", "Shortcake", "Shot Glass", "Sidewalk Enforcer", "Silly Goose", "Skull Crusher",
    "Sky Bully", "Slow Trot", "Small Fry", "Smart Cookie", "Smiley Face", "Snake Eyes", "Snappy",
    "Snicker Doodle", "Snow Bunny", "Snow Hound", "Snow Pea", "Snowflake", "Snuggle Able",
    "Snuggle Bear", "Soda Pop", "Sofa King", "Soul Friend", "Sparky", "Speedwell",
    "Springheel Jack", "Sprinkles", "Squatch", "Stacker of Wheat", "Star Bright", "Star Light",
    "Stepper", "Sugar Babe", "Sugar Bear", "Sugar Biscuit", "Sunflower", "Super Guy", "Swampmasher",
    "Sweet Kitten", "Sweet Tart", "Tacklebox", "Tarzan", "Tater Tot", "Tea Cup", "Teddy Bear",
    "Thrasher", "Toe", "Toolmaker", "Tough Guy", "Tough Nut", "Treasure Trove", "Turtle Dove",
    "Tweetie-Pie", "Tweetums", "Twinkle Toes", "Unicorn", "Unstoppable", "Vagabond Warrior",
    "Valentine", "Vortex", "Waffles", "Waylay Dave", "Wee-One", "Westie", "Wonder Guy",
    "Wonder Man", "Woo Bear", "Wookie", "Wordsmith", "Wuggle Bear", "Wuggles", "Xoxo", "Yankee",
    "Young Guy", "Youngest", "Yummers", "Zesty Dragon", "Abba Zabba", "Almond Joy", "Angel Wing",
    "Angelita", "Baby Carrot", "Baby Doll", "Baby Girl", "Baby Love", "Baby Spice", "Babycakes",
    "Bambi", "Bean", "Betty Boo", "Bite-size", "Blueberry Pie", "Bubble Gum", "Bugaboo", "Bugaloo",
    "Buggly Boo", "Bundt Cake", "Buttercup", "Butterfinger", "Butterscotch", "Candy Cane",
    "Cheezit", "Cherubie", "Chicken Tender", "Chicken Wing", "Cinnabon", "Cinnamon", "Corn Nut",
    "Cowgirl", "Cracker Jack", "Crispie Treat", "Critter", "Cuddle Bug", "Cuddly Boop",
    "Cuddly Duddly", "Cupcake", "Curls", "Curly-Q", "Curvy", "Cute Boot", "Cute Bot", "Cuteness",
    "Cutie", "Cutie Bug", "Cutie Buggles", "Cutie Cuddles", "Cutie Sniggles", "Cutie Snuggles",
    "Cutie Toes", "Cutie Wiggles", "Dibbles", "Dilly Dolly", "Dimples", "Dorito", "Double Bubble",
    "Double Love", "Double Stuff", "Double Trouble", "Dove", "Dovey Lovey", "Dum Dum", "Dumpling",
    "Fibbles", "Fillity Tuna", "Filly Billy", "French Fry", "Frito", "Funfetti", "Funion",
    "Fun-size", "Gaga", "Gibbles", "Giggles", "Glass of Sunshine", "Goal Baby", "Goddess", "Goldie",
    "Goldie Locks", "Goo Goo", "Green Love", "Gubble Bum", "Gumball", "Gumdrop", "Gummy Bear",
    "Gummy Worm", "Half Pint", "Heaven-Sent", "Honey Loaf", "Honeypot", "Hot French Fry",
    "Hot Potato", "Hot Sauce", "Hot Tater Tot", "Hurricane", "Icee Pop", "Ittle Skittle",
    "Itty Bitty Sugar Bomb", "Jammer", "Jelly Bean", "Jolly Rancher", "Junior Mint", "Khaki Lassie",
    "Kit Kat", "Lady Godiva", "Laffy Taffy", "Lervey Dervy", "Libbles", "Lifesaver",
    "Lil Antoinette", "Lil Ma’am", "Lioness", "Little Bear", "Little Rascal", "Lolli Lolli",
    "Lollipop", "Love on Fire", "Lovebug", "Lovey Tickles", "Luvvy Wuvvy", "M&M", "Mallow Cup",
    "Mama of Drama", "Maple Leaf", "Marshymallow", "Mi Novia-citita", "Milk Dud", "Misty May",
    "Monkey Toes", "Mooncake", "Muffin Butt", "Munchkin", "My Sunshine", "Nibbles", "Nutter Butter",
    "Okie", "Peaches", "Peach-o", "Peanut", "Pearly", "Pebbles", "Pickle", "Pink Starburst",
    "Pocket-size", "Pookie", "Pop Tart", "Pretty Love", "Princess Peach", "Principessa", "Punkin",
    "Quarter Note", "Raisenette", "Red-Hot Bon Bon", "Rocket Pop", "Sassy Lassy", "Secret Sauce",
    "Sex Witch", "Shortcake", "Sizzle Pop", "Sleeping Beauty", "Small Fry", "Smarty Pants",
    "Snackems", "Snizzle Snacks", "Snookums", "Snow White", "Snowflake", "Snuggle Wumps",
    "Snuggly Bear", "Sporty Spice", "Squirrel Sprout", "Steak Tip", "Sticky Bun", "Sugar Babe",
    "Sugar Bits", "Sugar Bomb", "Sugar Buns", "Sugar Lips", "Sugar Nova", "Sugar Plum",
    "Sugar Sauce", "Sugar Sugar", "Sunshine", "Supergirl", "Sushi", "Sweet Bun", "Sweet Eclair",
    "Sweet Heart", "Sweet Honey Love", "Sweet Loaf", "Sweet Mama", "Sweet Melody", "Sweet Pea",
    "Sweet Peach", "Sweet Tart", "Sweet Thing", "Sweetie Pie", "Swiss Roll",
    "Swizzly Sue Thompkins", "Tastee Squeeze", "Tater Tot", "Teddy Graham", "Teehee", "Thin Mint",
    "Tic Tac", "Tiffy Taffy", "Tigress", "Tiny One", "Tippy Tappy", "Toffee Lolly", "Tootsie Roll",
    "Tostito", "Triple Love", "Triscuit", "Tutti Frutti", "Tweety", "Twinkie", "Twinkle", "Twix",
    "Twizzle Top", "Waffles", "Whirly Pop", "Whoopie Pie", "Wonder Girl", "Wonder Woman", "Wuggles",
    "Yummy"]


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
    cleaned_cursive_text = re.sub(emoji_regex, ' ', cursive_text).strip(
    ) if not keep_emojis else cursive_text.strip()
    return cleaned_cursive_text


if __name__ == "__main__":
    # test
    print("9 outputs from RandomNoRepeats coin flips:")
    flipper = RandomNoRepeats(["heads", "tails"], "coins")
    print(", ".join(flipper.get_item() for i in range(9)))
