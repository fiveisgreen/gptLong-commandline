cat ./tests/test_API_readme.txt
python3 tests/gpt_simplest_API_test.py

cat ./tests/test_gpt_readme.txt
gpt "What is the capital of France?" --verbose

cat ./tests/test_gpte1_readme.txt
gpte -f tests/umerr.txt -o tests/out.txt -p 1 "Remove 'um's and other non-word blather from this transcript"

cat ./tests/test_gpte2_readme.txt
gpte -f tests/htmltable.txt -i tests/inst.txt
