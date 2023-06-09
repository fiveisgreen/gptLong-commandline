	  __________________________________    
	 / \                                \   
	|   |                               |   
	 \_ |                               |   
	    |          gpte TEST 1          |   
	    |                               |   
	    |   ____________________________|___
	    |  /                               /
	    \_/_______________________________/ 

Test Command: gpte -f data/umerr.txt -o data/out.txt "Remove 'um's and other non-word blather from this transcript"
This is a practical test of the gpte command, along with a demonstration of using it to clean up a transcript file data/umerr.txt
Contents of umerr.txt: "I um like to err go to the (sniff) store and uhh.. buy candy"
Expected output: "I like to go to the store and buy candy" and a pop-up text diff window.

