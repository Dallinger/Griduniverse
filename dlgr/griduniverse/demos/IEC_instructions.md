## Description
The `iec_demo.py` contains an interactive evolutionary computation experiment that allows a game's parameters to evolve to meet a fitness goal that maximizes a player's "fun" ratings. The program loops through the `N` x `M` experiments using the Dallinger API to generate experiments with parameters that get selected by each of the `N` members in the `M`th generation. Depending on the feedback score `N` players give, the `M+1`th generation returns a set of parameters that pass on the surviving genome to maximize the subsequent generation's feedback score. The program has a probability of making a random error during the copy of each gene, which is determined by the parameter `mutation_rate`. This process repeats until a final set of parameters are discovered.

## Evolve Class Parameters
Evolve(n, m, bots, mutation_rate)
- N is the number of single-player games run within a single generation.
- M is the number of generations, or how many cycles the outter loops runs.
- `bot` is a boolean that, when set to `True`, leads to `AdvantageSeekingBot` strategy to participate in the experiment automatically. When set to `False`, the experiments will be run manually.
- `mutation_rate` is the probability that any one gene will trigger a random mutation when copying each individual gene of the genome over to the next generation. It should be set to a decimal probability between 0 and 1.

## Running IEC with bots
1. Go into config.txt and set `webdriver_type=chrome`
2. If you do not have `chromedriver` installed, install (`brew install chromedriver` for Mac) and make sure you have the Google Chrome app (in your `/Applications` folder for Mac).
3. Make sure you've `pip` installed odo, pandas, and tablib into your environment.