# Expenses Visualizer
This tool provides a possibility to display expenses, such as credit card/account transactions in a graphical manner.
The program uses Python 3, matplotlib for the graph generation and PyQt5 for the GUI elements.


#### Supported formats
  - CSV (with or without header)
  - XLS files (must contain a header)
  
#### Categorization
For all transactions categories can be created. The categories can be specified by using a substring that will then categorize all transactions containing that string as part of the same category.

#### Requirements
 - Python 3
 - PyQt5
 - Matplotlib
 - xlrd
 - numpy
 - pandas
 - scipy
 
 The requirements can either be installed manually or via the provided *requirements.txt* file with

 `pip3 install -r requirements.txt`

after the installation the program can be run with

`python3 visualizer.py`

#### Usage
First an import folder containing the transaction files and the file type has to be specified . The files are analyzed automatically and a preview is presented.
The date format used in the files has to be specified as well as which columns represent *Date*, *Description* and *Amount*. The optional field *Balance* can also be specified but is not mandatory since not all exports might contain that column. 

NOTE: when specifying the balance column, the column must contain at least one row where a value is present. It is not necessary that all rows have that value, since the import will calculate the missing values automatically.

![Initial setup](https://github.com/svartkanin/Expenses-visualizer/blob/master/Screenshots/main_settings.png)

After specifying all necessary fields the data can be imported. Categories can be created in the *Manage categories* tab. The first table contains aliases which are used as a "category name". To each alias multiple sub-strings can be added, whereas each transaction description is search for these substrings. The unknown table at the bottom shows transactions that do not match any aliases.

![Category specification](https://github.com/svartkanin/Expenses-visualizer/blob/master/Screenshots/category_settings.png)

The analyzed data can then be viewed in various views:

![Overview](https://github.com/svartkanin/Expenses-visualizer/blob/master/Screenshots/overview.png)
![Category view](https://github.com/svartkanin/Expenses-visualizer/blob/master/Screenshots/categories.png)
