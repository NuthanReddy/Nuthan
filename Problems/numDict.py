words = ["abcd", "good", "food", "hoof", "hood"]


def get_num_repr(word):
    char_dict = {"a": "2", "b": "2", "c": "2", "d": "3", "e": "3", "f": "3", "o": "6", "g": "4", "h": "4"}
    num_char = ""
    for char in word:
        num_char += char_dict[char]
    return int(num_char)


def build_word_dict(words):
    word_dict = {}
    for word in words:
        num_repr = get_num_repr(word)
        try:
            word_dict[num_repr].append(word)
        except KeyError:
            word_dict[num_repr] = [word]
    return word_dict


word_dict = build_word_dict(words)
print(word_dict[4663])
