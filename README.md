# ukr_numbers
> [!WARNING]  
> This is a side project, currently pre-alpha. Sometimes it WILL be wrong, especially for longer numbers. You have been warned.

## What?
Convert int numbers (like "3") to (Ukrainian-language) words in 
a specific declination (третій/три/третьому/третьої).

The declination is given using natural language, that is you can decline any
simple number and it'll be used as example. E.g. if you want your 3/4 to 
become a "третьому"/"четвертому", you can enter "першому" as description. 

I find this easier than to remember whether you need an ordinal or not and 
what's the correct spelling of the name of the case for the result. 

## Examples
```bash
poetry run python3 -m ukr_numbers 8 два
вісім
poetry run python3 -m ukr_numbers 8 другої
восьмої
poetry run python3 -m ukr_numbers 8 другому
восьмому
poetry run python3 -m ukr_numbers 10 друге
десяте
```

`-1` is a special number denoting "last":
```bash
poetry run python3 -m ukr_numbers -1 два  #! can't decline it into a number
None
poetry run python3 -m ukr_numbers -1 другої
останньої
poetry run python3 -m ukr_numbers -1 другому
останньому
poetry run python3 -m ukr_numbers -1 друге
останнє
```

## Unsupported
- Nouns, like 'десятка', 'десяток'
- negative numbers, (except -1/last)
- numbers that take multiple words in Ukrainian (23 -> (currently) двадцят три)
	- they sometimes work, sometimes don't.
	- will be the next feature I'll look into

## Errors 
- if "останній"/last can't be inflected in the required way,
	(e.g. "перший"->"останній" is OK, "один"->??? isn't)
	None will be returned.
- if anything goes wrong and graceful_failure is enabled,
	in the worst case scenario the number itself will be
	returned as string (2 ->'2')

## Similar projects
Both used in this package:
- [num2words](https://github.com/savoirfairelinux/num2words)
	- multilingual incl. Ukrainian
	- can do inflection by case and partly by gender
	- can't do inflections together with ordinals
	- can't do adjectives (на ПЕРШОМУ місці)
- [pymorphy2](https://github.com/pymorphy2/pymorphy2) does inflection
