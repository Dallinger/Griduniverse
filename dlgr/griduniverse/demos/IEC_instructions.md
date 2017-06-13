## Running IEC with `bot=True` 
1. Go into config.txt and set `webdriver_type = chrome`
2. If you do not have chromedriver installed, install it and make sure you have the Chrome app in your Applications folder.
3. Make sure you've pip installed odo, pandas, and tablib into your environment (usually optional).

## Evolve class Parameters
Evolve(n, m, bots, mutation_rate)
M is the generations, how many cycles the outter loops runs.
M is the number of single-players per generation that measures survival.
`bot` is a boolean that, when `True`, leads to AdvantageSeekingBot strategy to run the program automatically. When `False` the experiments will be run manually
`mutation_rate` is the probability that any one gene will trigger a random mutation when copying each individual gene of the genome over to the next generation.
