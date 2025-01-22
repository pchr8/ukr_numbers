# ukr_numbers
> [!WARNING]  
> This is a side project. Sometimes it WILL be wrong, especially for longer numbers. You have been warned.
 
→
## Basics
### What?
Convert int numbers (`3`) to (Ukrainian-language) words in 
a specific declination (_третій/три/третьому/третьої_).

The target declination is given using natural language, in other words you _show_ the target declination instead of describing it.

FOR EXAMPLE, if you need "1→в першому вагоні", "2→в другому вагоні", "-1→в останньому вагоні", 
you can just enter "першому"  as your target declension, and all your integers
will be transformed to ordinals in the dative case.

It additionally supports `-1` as code for `last`, the output will be _останній_ declined in the same shape as the numeral would be.

### Why?
#### Declension target as natural language is neat
1. I find this easier than remembering the names of everything for an explicit target declension (is it ordinal or cardinal? do I write `dative` or `datv`? ..)
2. Automatic templating! I use this package to replace numbers in strings without the need to explicitly parse each one!

#### More features
Even without the natural language target bit, I found no packages that 
could convert integers to natural language while:
- handling both cardinals and ordinals 
- in different (grammatical) cases 
- agreeing to numbers and genders.

## Examples
```python
>>> from ukr_numbers import Numbers
>>> Numbers().convert_to_auto(231300,"другий")
WARNING:ukr_numbers.nums:Support for multi-word numbers (231300) is bad, errors are likely to happen, you're warned.
'двістітридцятьоднатисячатрьохсотий'
```

```bash
python3 -m ukr_numbers 8 два
вісім
python3 -m ukr_numbers 8 другої
восьмої

# `-1` is a special number denoting "last":
python3 -m ukr_numbers -1 два  #! can't decline it into a number
None
python3 -m ukr_numbers -1 другої
останньої

python3 -m ukr_numbers 124 першою
WARNING:ukr_numbers.nums:Support for multi-word numbers (124) is bad, errors are likely to happen, you're warned.
сто двадцять четвертою

python3 -m ukr_numbers -124 першою
WARNING:ukr_numbers.nums:Support for multi-word numbers (-124) is bad, errors are likely to happen, you're warned.
мінус сто двадцять четвертою
```

## Errors handling
- if "останній"/last can't be inflected in the required way,
	(e.g. "перший"→"останній" is OK, "один"→??? isn't)
	None will be returned.
- if anything goes wrong and `graceful_failure` is enabled,
	in the worst case scenario the number itself will be
	returned as string (2 →'2')

## Drawbacks
### Explicitly unsupported
- Nouns, like _десятка, десяток_
- Fractions (_дві з половиною тисячі_)

### Known bugs
- Numbers that take multiple words in Ukrainian (23 →  двадцять три) now have weak support, but..
- numbers composed of multiple words in certain _cases_ (pun intended) are only partially correct
	- e.g. (currently) 2000000+двома → два мільйонами, not _двома_ мільйонами
- **Please write tickets for edge cases you find!**

## Similar projects
Both used in this package:
- [num2words](https://github.com/savoirfairelinux/num2words)
	- multilingual incl. Ukrainian
	- can do inflection by case and partly by gender
	- can't do inflections together with ordinals
	- can't do adjectives (на ПЕРШОМУ місці)
- [pymorphy2](https://github.com/pymorphy2/pymorphy2) does inflection on natural words 
