'''
Given a string, return the character that appears the second most number of times in the string

The string will contain only ASCII characters, from the ranges ('a'-'z','A'-'Z','0'-'9')



Example

text = abbaac

'a' occurs 3 times, 'b' occurs 2 times and 'c' occurs 1 time in text.  So, 'b' is the answer.
'''

text = "abbaac"


def second_max(text):
    counts = {}
    for letter in text:
        try:
            counts[letter] = counts[letter] + 1
        except KeyError:
            counts[letter] = 1
    print(counts)
    max_v = None
    max_k = None
    sec_max_k = None
    sec_max_v = None
    for k, v in counts.items():
        print(max_v, max_k)
        if max_v is None or v > max_v:
            max_v = v
            max_k = k
        elif v < max_v and (sec_max_v is None or v > sec_max_v):
                sec_max_k = k
                sec_max_v = v
    return sec_max_k


print(second_max(text))