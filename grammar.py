def andify(things: list):
    """Helper function to put commas and spaces between the items in a list of things
    with appropriate placement of the word "and." 
    """
    if len(things) < 1:
        return ""
    return (f'{", ".join(things[:-1])}' +
            f'{", and " if len(things) > 2 else (" and " if len(things) > 1 else "")}' +
            f'{things[-1]}')


def copula(count: int) -> str:
    "Pluralization of the present tense of the English verb 'to be'"
    return "are" if count != 1 else "is"


def add_s(word: str, count: int) -> str:
    "Simple pluralization filter for words"
    return word+"s" if count != 1 else word


def num(number: int) -> str:
    """Formats numbers; those less than ten are turned into words; those greater than
    999 have commas placed appropriately"""
    numbers = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
               6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
    if number in numbers:
        return numbers[number]
    else:
        return f"{number:,}"
