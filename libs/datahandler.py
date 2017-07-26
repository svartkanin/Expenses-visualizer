from collections import OrderedDict
from time import strptime
import os
import calendar
import re
import json
import pandas as pd
from io import StringIO
from locale import *
setlocale(LC_NUMERIC, '')


class DataHandler:

	def __init__(self, sett):
		self._settings = sett
		self._data_container = self._import_files()
		self._definitions_data = self._get_category_def()
		self._categories_container = self._calculate_categories()

	def _get_category_def(self):
		"""
			Retrieve category definitions
		"""
		self._definitions_path = self._settings.import_dir + os.sep + self._settings.category_def_dir
		if os.path.isfile(self._definitions_path):
			with open(self._definitions_path, 'r') as fp:
				return json.load(fp, object_pairs_hook=OrderedDict)
		else:
			return OrderedDict({'categories': {}})

	def _check_uncategorized(self, uncategorized):
		"""
			Handle uncategorized entries from import data
		"""
		if not uncategorized.empty:
			rows = [row.strip() for row in uncategorized[[self._settings.column_description]].to_string(index=False, header=False).split('\n')]
			unknown = set(self._definitions_data['categories'].setdefault('Unknown', []))
			self._definitions_data['categories']['Unknown'] = list(unknown | set(rows))
			self._write_definitions()

	def _write_definitions(self):
		"""
			Write definitions container to file
		"""
		with open(self._definitions_path, 'w') as fp:
			json.dump(self._definitions_data, fp, indent=4)

	def update_entries(self, entry1, entry2, action, new_value=''):
		"""
			Update category definitions
		"""
		if action == 'delete':
			if entry1 and not entry2:
				del self._definitions_data['categories'][entry1]
			elif entry1 and entry2:
				self._definitions_data['categories'][entry1].remove(entry2)
		elif action == 'update':
			if entry2 is None:
				if entry1 != '':
					self._definitions_data['categories'] = OrderedDict([(new_value, v) if k == entry1 else (k, v) for k, v in self._definitions_data['categories'].items()])
				else:
					self._definitions_data['categories'][new_value] = []
			else:
				if entry2 != '':
					self._definitions_data['categories'][entry1] = [new_value if x == entry2 else x for x in self._definitions_data['categories'][entry1]]
				else:
					self._definitions_data['categories'][entry1].append(new_value)

		self._write_definitions()

	def get_category_aliases(self):
		"""
			Retrieve all defined aliases
		"""
		return list(self._definitions_data['categories'].keys())

	def get_categories(self, alias):
		"""
			Retrieve categories for corresponding alias
		"""
		try:
			return self._definitions_data['categories'][alias]
		except:
			return []

	def _cb_str_to_float(self, string):
		"""
			Callback function for csv read to get the possible float from a string
		"""
		try:
			if '.' in string and ',' in string:
				pos1 = string.find('.')
				pos2 = string.find(',')
				if pos1 > pos2:
					string = string.replace(',', '', 1)
				else:
					string = string.replace('.', '', 1)

			return atof(string)
		except:
			return None

	def _cb_date_parser(self, x):
		"""
			Callback function for csv read to get correct date format
		"""
		try:
			return pd.datetime.strptime(x, self._settings.date_format)
		except TypeError:
			raise TypeError("Parsing to date format failed for value: " + repr(x))

	def _prepare_import_file(self, file):
		"""
			Load import data from file and if not present add a custome header to the data
		"""
		with open(file, 'r') as fp:
			data = fp.read()
			if not self._settings.has_header:
				try:
					data = self._settings.custom_header + data
				except Exception:
					raise ValueError('Header missing!')
			return StringIO(data)

	def _import_csv(self, import_data):
		"""
			Import csv data into pandas dataframe
		"""
		return pd.read_csv(import_data,
		                   delimiter=self._settings.delimiter,
		                   header=0,
		                   parse_dates=[self._settings.column_date],
		                   date_parser=self._cb_date_parser,
		                   converters={self._settings.column_amount: self._cb_str_to_float,
		                               self._settings.column_balance: self._cb_str_to_float})

	def _import_files(self):
		"""
			Import the data files
		"""
		container = pd.DataFrame()
		for file in self._settings.import_files:
			try:
				if self._settings.file_type == 'csv':
					import_data = self._prepare_import_file(file)
					df = self._import_csv(import_data)
					container = pd.concat([container, df]).reset_index(drop=True)
			except (ValueError, TypeError) as ve:
				raise ImportError('Import error occured with file:\n' + file + '\n' + ve.args[0])

		return container

	def _get_month_name(self, month):
		"""
			Retrieve the month name for an integer 1-12
		"""
		return calendar.month_name[month]

	def _search_uncategorized(self, categories, df):
		"""
			Retrieve all data sets from dataframe that are not covered by any category
		"""
		regex = '|'.join(['%s' % ('|'.join(i)) for i in categories])
		if regex:
			return df[~df[self._settings.column_description].str.contains(regex, flags=re.IGNORECASE)]
		else:
			return df

	def _get_date_legend(self, date):
		"""
			Retrieve unique date string year:month
		"""
		return str(date[0]) + ":" + self._get_month_name(date[1])

	def _calculate_categories(self):
		"""
			Calculate the category blocks from import data
		"""
		category_defs = self._definitions_data['categories']
		grouped_months = self._get_grouped_months()  # import data grouped by month
		results = OrderedDict()
		uncategorized = pd.DataFrame()

		for date, df in grouped_months:
			# only interested in expenses
			df_exp = df[df[self._settings.column_amount] < 0]
			category_container = OrderedDict()

			for alias, categories in category_defs.items():
				# create an OR regex for all categories for an alias
				regex = '|'.join(['%s' % i for i in categories])
				# apply regex to the dataframe, filtering all matching datasets for the current alias
				df_filtered = df_exp[df_exp[self._settings.column_description].str.contains(regex, flags=re.IGNORECASE)]
				# calculate the sum and abs for all filtered data sets to be displayed
				category_container[alias] = abs((df_filtered[self._settings.column_amount].values.sum()))

			# check if any data sets have not been categorized
			category_container.setdefault('Unknown', 0)
			no_categories = self._search_uncategorized(category_defs.values(), df_exp)
			if not no_categories.empty:
				val = abs((no_categories[self._settings.column_amount].values.sum()))
				category_container['Unknown'] += val
				uncategorized = uncategorized.append(no_categories)

			results[self._get_date_legend(date)] = category_container

		self._check_uncategorized(uncategorized)
		return results

	def get_total_in_out(self, df=None):
		"""
			Calculate total income and output from a data set
		"""
		col_amount = self._settings.column_amount
		if df is None:
			df = self._data_container

		df_output = df[df[col_amount] < 0]
		output = abs(df_output[col_amount].values.sum())

		df_input = df[df[col_amount] > 0]
		income = abs(df_input[col_amount].values.sum())

		return income, output

	def get_total_day(self, overall=False, reverse=False):
		"""
			Retrieve per day results of expenses
		"""
		amount_col = self._settings.column_amount
		# filter only expenses
		df = self._data_container[self._data_container[amount_col] < 0].reset_index()

		if not overall:
			df[amount_col] = df[amount_col].apply(lambda x: abs(x))

		res = df.groupby([self._settings.column_date])[[amount_col]].sum().reset_index()
		res = OrderedDict({row[self._settings.column_date]: row[self._settings.column_amount] for i, row in res.iterrows()})
		return OrderedDict(sorted(res.items(), key=lambda x: pd.to_datetime(x[0]), reverse=reverse)), self._settings.date_format

	def _get_grouped_months(self):
		"""
			Retrieve data sets grouped by month and year
		"""
		return pd.groupby(self._data_container, by=[self._data_container[self._settings.column_date].dt.year, self._data_container[self._settings.column_date].dt.month])

	def get_total_month(self):
		"""
			Retrieve per month results
		"""
		grouped_months = self._get_grouped_months()
		results = OrderedDict()

		for date, df in grouped_months:
			results[self._get_date_legend(date)] = self.get_total_in_out(df)

		return results

	def _get_month_from_key(self, value):
		"""
			Retrieve month/year value from given string year:month
		"""
		year, month = value.split(':')
		return int(year), strptime(month, '%B').tm_mon

	def get_categorized_data_sets(self, selected_date, category):
		"""
			Retrieve categorized results
		"""
		year, month = self._get_month_from_key(selected_date)
		col_date = self._settings.column_date
		col_desc = self._settings.column_description

		categories = self._definitions_data['categories'][category]
		regex = '|'.join(['%s' % i for i in categories])

		# filter all data sets for year and month
		df_filtered = self._data_container[(self._data_container[col_date].dt.year == year) & (self._data_container[col_date].dt.month == month)]
		df_filtered = df_filtered[df_filtered[col_desc].str.contains(regex, flags=re.IGNORECASE)]
		df_filtered[self._settings.column_date] = df_filtered[self._settings.column_date].apply(lambda x: x.strftime(self._settings.date_format))

		return df_filtered[[self._settings.column_date, self._settings.column_description, self._settings.column_amount]].reset_index()

	def _calc_balances(self, df, date, balance):
		"""
			Some files might miss the balances in some rows;
			this function calculates all balances by taking the latest
			found balance value and recursively calculating all others
			taking the expenses/earnings
		"""
		col_date = self._settings.column_date
		indexes = reversed(list(df.index)[:-1])

		for idx in indexes:
			if df.ix[idx][col_date] <= date:
				val = balance - df.get_value(idx+1, 'cumsum')
			else:
				val = balance + df.get_value(idx+1, 'cumsum')
			df.set_value(idx, 'new_balance', val)

		return df

	def get_days_balance(self):
		"""
			Retrieve per day balances
		"""
		if self._data_container[self._settings.column_balance].isnull().values.any():
			# determine balance value for most recent date
			df_sorted = self._data_container.sort_values(by=self._settings.column_date, ascending=True).reset_index()
			last_valid_val = df_sorted[self._settings.column_balance].last_valid_index()
			date = df_sorted.ix[last_valid_val][self._settings.column_date]
			balance = df_sorted.ix[last_valid_val][self._settings.column_balance]

			# group all values by day and sum the in/out transacitons;
			# go through all days and sum up all amounts recursively
			# apply the found balance value to all amounts the receive the daily balance recursively
			df_grouped = df_sorted.groupby([self._settings.column_date])[[self._settings.column_amount]].sum().reset_index()
			df_grouped['cumsum'] = df_grouped[::-1][self._settings.column_amount].cumsum()
			df_grouped = self._calc_balances(df_grouped, date, balance)

			df = df_grouped.rename(columns={'new_balance': self._settings.column_balance})
		else:
			df = self._data_container[[self._settings.column_date, self._settings.column_balance]]

		res = OrderedDict({row[self._settings.column_date]: row[self._settings.column_balance] for idx, row in df.iterrows()})
		return OrderedDict(sorted(res.items(), key=lambda x: pd.to_datetime(x[0]))), self._settings.date_format

	def get_calculated_categories(self):
		"""
			Retrieve categorized results
		"""
		return self._categories_container

	def get_search_data(self, search_string=''):
		"""
			Retrieve data to be displayed in the search table
		"""
		df = self._data_container.sort_values(by=self._settings.column_date, ascending=False).reset_index()
		df = df[[self._settings.column_date, self._settings.column_description, self._settings.column_amount]].reset_index()
		df[self._settings.column_date] = df[self._settings.column_date].apply(lambda x: x.strftime(self._settings.date_format))

		# search conditions
		cond = df[self._settings.column_description].str.contains(search_string, flags=re.IGNORECASE) | \
		       df[self._settings.column_date].str.contains(search_string) | \
		       df[self._settings.column_amount].apply(lambda x: str(x)).str.contains(search_string)

		return df[cond]

	def get_column_headers(self):
		"""
			Retrieve the column headers to be displayed in the category tables
		"""
		df = pd.DataFrame(columns=[self._settings.column_date, self._settings.column_description, self._settings.column_amount]).reset_index()
		return df
