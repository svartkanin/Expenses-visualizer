import csv
import os


class Settings:

	def __init__(self):
		self.category_def_dir = 'category_definitions.json'
		self.available_extensions = ['csv']
		self.available_date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y', '%Y-%d-%m']
		self.header = []
		self.has_header = False
		self.delimiter = None
		self.file_type = None
		self.import_files = None
		self.column_date = None
		self.column_description = None
		self.column_amount = None
		self.column_balance = None
		self.date_format = None
		self.import_dir = None

		self._preview_data = None

	def get_table_headers(self):
		"""
			Retrieve table headers relevant for display
		"""
		return [self.column_date, self.column_description, self.column_amount]

	def _create_custom_header(self, settings):
		"""
			In case no header was provided in the import file, a custom
			header has to be created filled with the necessary header fields
		"""
		# these are the column definitions from the settings tab
		# stored in form of a mapping dictionary (1: 'Date', 2: 'Description'...)
		def_cols = {settings['date_col']: self.column_date,
		            settings['description_col']: self.column_description,
		            settings['amount_col']: self.column_amount,
		            settings['balance_col']: self.column_balance}

		header = ''
		# Loop through all columns of the import file
		for i in range(0, len(self._preview_data[0])):
			# the columns that can be mapped to the above dict are filled with the corresponding names
			# other columns that are not needed for data processing still have to be named something
			# otherwise the has_header check will fail due to empty column names
			attach = def_cols[i] if i in def_cols.keys() else 'Dummy'
			header = header + (',' if header else '') + attach
		return header + '\n'

	def set_import_settings(self, settings):
		"""
			Set import settings from the settings tab
		"""
		self.import_dir = settings['import_dir']
		self.file_type = settings['file_type']
		self.date_format = settings['date_format']

		if self.has_header:
			self.column_date = self.header[settings['date_col']]
			self.column_description = self.header[settings['description_col']]
			self.column_amount = self.header[settings['amount_col']]
			self.column_balance = self.header[settings['balance_col']]
		else:
			self._set_default_col_names()
			self.header = self._create_custom_header(settings)

	def _set_default_col_names(self):
		"""
			Specify default column names in case no header has been provided in the import file
		"""
		self.column_date = 'Date'
		self.column_description = 'Description'
		self.column_amount = 'Amount'
		self.column_balance = 'Balance'

	def sniff_import_dir(self, import_dir, file_type):
		"""
			Analyze the import files and determine some characteristics such as
			delimiter and header
		"""
		# check all files in the import directory with the allowed file types
		self.import_files = []
		for file in os.listdir(import_dir):
			if os.path.splitext(file)[1][1:] in file_type:
				self.import_files.append(os.path.join(import_dir, file))

		if self.import_files:
			# pick a test file to analyze
			# this assumes that all files that have to be imported are
			# of the same structure (header, columns...)
			test_file = self.import_files[0]

			if file_type == 'csv':
				with open(test_file, 'r') as fp:
					sniffer = csv.Sniffer()
					data = fp.readlines()
					dialect = sniffer.sniff(''.join(data))
					self.delimiter = dialect.delimiter

					if sniffer.has_header(''.join(data)):
						self.has_header = True
						self.header = data[0].strip().split(self.delimiter)

					self._preview_data = list(csv.reader(data, delimiter=self.delimiter, quotechar=dialect.quotechar))
					return self._preview_data[:10]
