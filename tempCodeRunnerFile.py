from exa_py import Exa

exa = Exa('c7da9420-64e2-4aca-8a26-90c01ebe5305')
query = input('Search here: ')

response = exa.search(
    query,
    num_results=5,
    text=True,
  