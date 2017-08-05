import sys
from libs.mainwindow import Ui_MainWindow
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import QSize, Qt
from libs.analysis import Analysis
from libs.settings import Settings
from libs.datahandler import DataHandler
import datetime


class CustomTabWidget(QTabBar):
	"""
		Custom tab widget to align tabs left and beneath each other
	"""
	def __init__(self, *args, **kwargs):
		self.tabSize = QSize(kwargs.pop('width'), kwargs.pop('height'))
		super(CustomTabWidget, self).__init__(*args, **kwargs)

	def paintEvent(self, event):
		painter = QStylePainter(self)
		option = QStyleOptionTab()

		painter.begin(self)
		for index in range(self.count()):
			self.initStyleOption(option, index)
			tab_rect = self.tabRect(index)
			tab_rect.moveLeft(10)
			painter.drawControl(QStyle.CE_TabBarTabShape, option)
			painter.drawText(tab_rect, Qt.AlignVCenter | Qt.TextDontClip, self.tabText(index))
		painter.end()

	def tabSizeHint(self, index):
		return self.tabSize


class Visualizer(QMainWindow, Ui_MainWindow):

	def __init__(self):
		super(self.__class__, self).__init__()
		self.setupUi(self)
		self.setFixedSize(self.frameGeometry().width(), self.frameGeometry().height())
		self._categories_table_container = dict()
		self._imported = False
		self._sett_cat_table_dc = None
		self._cb_selection_text = 'Select'

		# SETTINGS
		self._settings = Settings()

		# SIGNALS
		self._setup_signals()
		# init the selection with the first value
		self._cb_date_format()

		# Set buttons enabled/disabled
		self._cb_enable_disable_controls()

		# Set tabs enabled/disabled
		self._enable_disable_tabs()

	def _setup_signals(self):
		"""
			Initializes the settings tab (comboboxes, radio buttons...)
		"""
		self.but_import_dir.clicked.connect(self._cb_import_dir)

		# FILE TYPE
		file_types = [self._cb_selection_text] + self._settings.available_extensions
		self.cb_file_type.addItems(file_types)
		self.cb_file_type.currentIndexChanged.connect(self._cb_file_type)

		# DATE FORMAT
		date_types = [self._cb_selection_text] + self._settings.available_date_formats
		self.cb_date_format.addItems(date_types)
		self.cb_date_format.currentIndexChanged.connect(self._cb_date_format)

		# COLUMN DEFINITIONS
		self.date_col.currentIndexChanged.connect(self._cb_enable_disable_controls)
		self.description_col.currentIndexChanged.connect(self._cb_enable_disable_controls)
		self.amount_col.currentIndexChanged.connect(self._cb_enable_disable_controls)
		self.balance_col.currentIndexChanged.connect(self._cb_enable_disable_controls)

		# IMPORT BUTTON
		self.but_import.clicked.connect(self._cb_but_import_clicked)

		# SEARCH
		self.search_field.textChanged.connect(self._cb_search_field_changed)

	def _clear_layout(self, layout):
		"""
			Deletes all children of given layout
		"""
		while layout.count():
			child = layout.takeAt(0)
			if child.widget():
				child.widget().deleteLater()

	def _cb_search_field_changed(self):
		"""
			Callback function for the search field text
		"""
		search_text = self.search_field.text()
		self._set_search_tab_table(self._data_handler.get_search_data(search_text))

	def _clear_all(self):
		"""
			Clear existing views of all their widgets
			needed in case the import is performed multiple times
		"""
		self._analysis.reset_plots()
		self._clear_layout(self.overview_graph_hbox)
		self._clear_layout(self.month_graph_hbox)
		self._clear_layout(self.day_expenses_vbox)
		self._clear_layout(self.balance_vbox)
		self._clear_layout(self.single_categories_container)

	def _enable_disable_tabs(self):
		"""
			Enable/Disable tabs if data has been imported already or not
		"""
		self.main_tab_widget.setTabEnabled(1, self._imported)
		self.main_tab_widget.setTabEnabled(2, self._imported)
		self.main_tab_widget.setTabEnabled(3, self._imported)
		self.main_tab_widget.setTabEnabled(4, self._imported)
		self.sub_settings.setTabEnabled(1, self._imported)

	def _show_msg_box(self, severity, text):
		"""
			Prompt different message boxes;
			severity defines the type of the message box (info, warning or critical)
		"""
		msg = QMessageBox()
		if severity == 'info':
			msg.setIcon(QMessageBox.Information)
			msg.setWindowTitle("Information")
		elif severity == 'warning':
			msg.setIcon(QMessageBox.Warning)
			msg.setWindowTitle("Warning")
		elif severity == 'critical':
			msg.setIcon(QMessageBox.Critical)
			msg.setWindowTitle("Error")
		else:
			raise ValueError("Unknown severity: '" + severity + "'")

		msg.setText(text)
		msg.setStandardButtons(QMessageBox.Ok)
		msg.exec_()

	def _cb_sett_categories_text_changed(self, item, table):
		"""
			Callback function to handle a modification of a table entry
		"""
		# only proceed if the value has been changed by hand (e.g. double click to cell earlier)
		# should not be triggered if values are changed due to loading of data
		if self._sett_cat_table_dc is not None:
			new_value = item.text()
			if table == self.sett_category_aliases_tab:
				old_value = cur_alias = self._sett_cat_table_dc
				cur_categ = None
			else:
				old_value = cur_categ = self._sett_cat_table_dc
				cur_alias = self.sett_category_aliases_tab.currentItem().text()

			if old_value is not None:
				# if value has been changed to empty string -> set back to old value
				if new_value == '':
					item.setText(old_value)
				elif new_value != old_value:
					self._data_handler.update_entries(cur_alias, cur_categ, 'update', new_value)
				self._sett_cat_table_dc = None

			self._update_category_changes()

	def _cb_sett_categories_double_click(self, table):
		"""
			Callback function to record manual item changes
		"""
		if table == self.sett_category_aliases_tab:
			cur_item = self.sett_category_aliases_tab.currentItem()
		else:
			cur_item = self.sett_categories_tab.currentItem()

		if cur_item:
			self._sett_cat_table_dc = cur_item.text()
		else:
			self._sett_cat_table_dc = ''

	def _load_tab_categories_data(self, data, table):
		"""
			Fill table with data
		"""
		table.setRowCount(len(data))
		for i in range(len(data)):
			table.setItem(i, 0, QTableWidgetItem(data[i]))

	def _cb_alias_changed(self):
		"""
			Callback function to reload data for the category browser when a different alias is selected
		"""
		selection = self.sett_category_aliases_tab.selectedItems()
		data = []
		if selection:
			sel_item = selection[0].text()
			data = self._data_handler.get_categories(sel_item)

		# reload the data data for categories table
		self._load_tab_categories_data(data, self.sett_categories_tab)

	def _setup_setting_tables(self, table, data, headers):
		"""
			Setup table with corresponding data and header columns
		"""
		table.setColumnCount(len(headers))
		table.setHorizontalHeaderLabels(headers)

		# context menus are triggered by right click
		# they can be used to remove or add rows to a table
		table.setContextMenuPolicy(Qt.CustomContextMenu)
		table.customContextMenuRequested.connect(lambda cell: self._cb_table_context_menu(cell, table))

		# callbacks to handle alias/category text changes
		table.itemChanged.connect(lambda item: self._cb_sett_categories_text_changed(item, table))
		table.cellDoubleClicked.connect(lambda: self._cb_sett_categories_double_click(table))

		# fill tables with existing data
		self._load_tab_categories_data(data, table)

		# set header to fill up entire length
		header = table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.Stretch)

	def _setup_category_definitions(self):
		"""
			Setup category defintions tables
		"""
		# initialize the alias table with existing aliases from the definitions file
		aliases = self._data_handler.get_category_aliases(incl_unknown=False)
		self._setup_setting_tables(self.sett_category_aliases_tab, aliases, ['Aliases'])
		self.sett_category_aliases_tab.itemSelectionChanged.connect(self._cb_alias_changed)

		# setup the categories table of the aliases
		self._setup_setting_tables(self.sett_categories_tab, [], ['Categories'])

		# setup the unknown categories table
		unknown = self._data_handler.get_unknown_categories()
		self._setup_setting_tables(self.sett_categories_unknown_tab, unknown, ['Unknown'])

		# Auto select the first row
		self.sett_category_aliases_tab.selectRow(0)

	def _get_cell_val(self, cell, table):
		"""
			Retrieve the text value of a cell from table
		"""
		idx = table.indexAt(cell)
		w = table.item(idx.row(), idx.column())
		return w.text()

	def _add_new_row(self, table):
		"""
			Add a new empty row to table; only if there is currently no empty row present
			this should work since the value of existing rows cannot be set to an empty string
		"""
		rows = table.rowCount()
		for i in range(rows):
			if not table.item(i, 0) or not table.item(i, 0).text():
				return
		table.insertRow(rows)

	def _remove_entry(self, entry, table):
		"""
			Removes the entry of a table
		"""
		# to avoid accidents, each removable has to be confirmed again
		msg = "Are you sure you want to delete this entry?"
		reply = QMessageBox.question(self, 'Message', msg, QMessageBox.Yes, QMessageBox.No)

		# only remove if confirmed
		if reply == QMessageBox.Yes:
			if table == self.sett_category_aliases_tab:
				self._data_handler.update_entries(self._get_cell_val(entry, table), '', 'delete')
			elif table == self.sett_categories_tab:
				self._data_handler.update_entries(self.sett_category_aliases_tab.currentItem().text(), self._get_cell_val(entry, table), 'delete')
			table.removeRow(table.rowAt(entry.y()))
			self._update_category_changes()

	def _update_category_changes(self):
		"""
			Update category changes and reload category tab
		"""
		unknown = self._data_handler.get_unknown_categories()
		self._setup_setting_tables(self.sett_categories_unknown_tab, unknown, ['Unknown'])
		# lazy way of updating category changes is to reload every tab
		# done this way because otherwise the single graphs of the category tab would
		# have to be remember to be deleted from the plt
		# if they wouldn't be deleted then the are constantly added and cause high memory usage
		self._init_all_tabs()

	def _cb_table_context_menu(self, cell, table):
		"""
			Callback function to show context menu for table on right click
		"""
		menu = QMenu(self)
		add_action = QAction('Add entry', self)
		add_action.triggered.connect(lambda: self._add_new_row(table))
		menu.addAction(add_action)

		rem_action = QAction('Delete entry', self)
		rem_action.triggered.connect(lambda: self._remove_entry(cell, table))
		menu.addAction(rem_action)

		menu.popup(QCursor.pos())

	def _init_all_tabs(self):
		"""
			Init all tabs with the corresponding data to display
		"""
		self._clear_all()
		self._set_overview_tab()
		self._set_day_overview_tab()
		self._set_category_detail_tab()
		self._set_search_tab()

	def _cb_but_import_clicked(self):
		"""
			Callback function from import button
			this will trigger the import of the data and setup of all components
		"""
		if self._settings.import_files:
			imp_settings = {'import_dir': self.import_dir.text(),
			                'file_type': self.cb_file_type.currentText(),
			                'date_format': self.cb_date_format.currentText(),
			                'date_col': int(self.date_col.currentText())-1,
			                'description_col': int(self.description_col.currentText())-1,
			                'amount_col': int(self.amount_col.currentText())-1,
			                'balance_col': int(self.balance_col.currentText())-1}

			try:
				self._settings.set_import_settings(imp_settings)
				self._data_handler.import_data(self._settings)
				self._setup_category_definitions()
				self._analysis = Analysis(self._data_handler, self.cb_category_table)

				self._init_all_tabs()

				self._imported = True
				self._enable_disable_tabs()
				self._data_handler.save_settings()
			except ImportError as e:
				self._show_msg_box('critical', e.args[0])
			except (ValueError, AttributeError):
				self._show_msg_box('critical', 'Error during data analysis occured!\nMight the defined columns be wrong?')
		else:
			self._show_msg_box('warning', 'No files found to import!')

	def _cb_rb_other(self, enabled):
		"""
			Callback function for the 'other' radio button, indicating that a different
			separator as the ones provided is going to be entered
		"""
		self.sep_other.setEnabled(enabled)
		if not enabled:
			self.sep_other.setText('')

	def _init_defaults(self, preview_data):
		"""
			Init some settings with default parameters
		"""
		if preview_data:
			selections = [self._cb_selection_text]
			selections.extend([str(i) for i in range(1, len(preview_data[0])+1)])

			self._set_table_entries(self.data_preview_tab, preview_data)
			self.date_col.addItems(selections)
			self.description_col.addItems(selections)
			self.amount_col.addItems(selections)
			self.balance_col.addItems(selections)

	def _set_settings(self, sett):
		"""
			Set saved settings
		"""
		if 'file_type' in sett: self.cb_file_type.setCurrentText(sett['file_type'])
		if 'date_format' in sett: self.cb_date_format.setCurrentText(sett['date_format'])
		if 'columns' in sett:
			columns = sett['columns']
			if 'date' in columns: self.date_col.setCurrentText(columns['date'])
			if 'description' in columns: self.description_col.setCurrentText(columns['description'])
			if 'amount' in columns: self.amount_col.setCurrentText(columns['amount'])
			if 'balance' in columns: self.balance_col.setCurrentText(columns['balance'])

	def _cb_import_dir(self):
		"""
			Callback function for the selection of the import directory
		"""
		self._import_dir = QFileDialog.getExistingDirectory(self, "Select import directory")
		if self._import_dir:
			self.import_dir.setText(self._import_dir)
			self.cb_file_type.setCurrentText(self._cb_selection_text)
			self._cb_enable_disable_controls()

			self._settings.import_dir = self._import_dir
			self._data_handler = DataHandler(self._settings)
			loaded_settings = self._data_handler.get_settings()
			if loaded_settings:
				self._set_settings(loaded_settings)

	def _cb_date_format(self):
		"""
			Callback function for the date format selection combobox
			this will simply trigger the display of the example value
		"""
		if self.cb_date_format.currentText() != self._cb_selection_text:
			text = datetime.datetime.strptime('1920-11-23', '%Y-%m-%d').strftime(self.cb_date_format.currentText())
			self.date_format.setText(text)
		else:
			self.date_format.setText('')
		self._cb_enable_disable_controls()

	def _cb_file_type(self):
		"""
			Callback function for file type selection
		"""
		if self.cb_file_type.currentText() != self._cb_selection_text:
			preview_data = self._settings.sniff_import_dir(self._import_dir, self.cb_file_type.currentText())
			self._init_defaults(preview_data)
		else:
			self._enable_disable_col_def(False)

		self._cb_enable_disable_controls()

	def _check_column_defs(self):
		"""
			Checks if all column specifications of the import data have been set
		"""
		if self.date_col.currentText() != self._cb_selection_text and \
				self.description_col.currentText() != self._cb_selection_text and \
				self.amount_col.currentText() != self._cb_selection_text and \
				self.balance_col.currentText() != self._cb_selection_text:
			return True
		else:
			return False

	def _enable_disable_col_def(self, enable):
		"""
			Enable/disable column control boxes and their content
		"""
		self.date_col.setEnabled(enable)
		self.description_col.setEnabled(enable)
		self.amount_col.setEnabled(enable)
		self.balance_col.setEnabled(enable)

		if not enable: self._set_table_entries(self.data_preview_tab, [])
		if not enable: self.date_col.clear()
		if not enable: self.description_col.clear()
		if not enable: self.amount_col.clear()
		if not enable: self.balance_col.clear()

	def _cb_enable_disable_controls(self):
		"""
			Callback function triggered when setting various controls
		"""
		# Disable controls if no import directory is specified yet
		enable = True if self.import_dir.text() else False
		self.cb_file_type.setEnabled(enable)
		if not enable: self.cb_file_type.setCurrentText(self._cb_selection_text)

		# Disable control if no file type has been specified yet
		if self.cb_file_type.currentText() == 'csv':
			enable = self.cb_file_type.currentText() != self._cb_selection_text
		else:
			enable = False

		self.cb_date_format.setEnabled(enable)
		# self._enable_disable_rb(enable)
		self._enable_disable_col_def(enable)
		if not enable: self.cb_date_format.setCurrentText(self._cb_selection_text)

		# Disable import button if not all required fields are set
		enable = True if (self.import_dir.text() and
		                 self.cb_file_type.currentText() != self._cb_selection_text and
		                 self.cb_date_format.currentText() != self._cb_selection_text and
		                 self._check_column_defs()) else False
		self.but_import.setEnabled(enable)

	def _set_search_tab_table(self, df):
		"""
			Setup the search tab table
		"""
		self._set_table_entries_df(self.search_results, df)
		header = self.search_results.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.Stretch)
		header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

	def _set_search_tab(self):
		"""
			Setup search tab
		"""
		self._set_search_tab_table(self._data_handler.get_search_data())

	def _set_overview_tab(self):
		"""
			Setup overview tab
		"""
		self.overview_graph_hbox.addWidget(self._analysis.create_overall_overview())
		self.month_graph_hbox.addWidget(self._analysis.create_monthly_overview())

	def _set_day_overview_tab(self):
		"""
			Setup day overview tab
		"""
		self.day_expenses_vbox.addWidget(self._analysis.create_day_overview())
		self.balance_vbox.addWidget(self._analysis.create_day_balance())

	def _wrap_widget(self, t_type, widget, width=0, height=0, margins=None, align=None):
		"""
			Wraps passed widget into a specified outer layout
		"""
		wrapper = QWidget()

		if t_type == 'hbox':
			wrapper.layout = QHBoxLayout()
		elif t_type == 'vbox':
			wrapper.layout = QVBoxLayout()

		if type(widget) == list:
			for w in widget:
				if align:
					wrapper.layout.addWidget(w, alignment=align)
				else:
					wrapper.layout.addWidget(w)
		else:
			if align:
				wrapper.layout.addWidget(widget, alignment=align)
			else:
				wrapper.layout.addWidget(widget)

		if height > 0:
			wrapper.setFixedHeight(height)
		if width > 0:
			wrapper.setFixedWidth(width)
		if margins and len(margins) == 4:
			wrapper.layout.setContentsMargins(margins[0], margins[1], margins[2], margins[3])

		wrapper.setLayout(wrapper.layout)
		return wrapper

	def _set_category_table(self, table, df):
		"""
			Setup category table
		"""
		self._set_table_entries_df(table, df)
		header = table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.Stretch)

	def _create_category_layout(self, fig, name):
		"""
			Create a category layout to store the figure
		"""
		table_widget = QTableWidget()
		table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
		table_widget.setSortingEnabled(True)

		graph = self._wrap_widget('hbox', fig, height=300, align=Qt.AlignCenter)
		table = self._wrap_widget('hbox', table_widget)
		container = self._wrap_widget('vbox', [graph, table])

		self._categories_table_container[name] = table_widget
		self._set_category_table(table_widget, self._data_handler.get_column_headers())

		container.layout.setAlignment(Qt.AlignCenter)

		return container

	def _set_table_entries(self, table, data):
		"""
			Set table data from list
		"""
		if data:
			table.setRowCount(len(data))
			table.setColumnCount(len(data[0]))

			for i in range(len(data)):
				for j in range(len(data[0])):
					table.setItem(i, j, QTableWidgetItem(str(data[i][j])))
		else:
			table.setRowCount(0)

	def _set_table_entries_df(self, table, df):
		"""
			Set table data from dataframe
		"""
		# table.setRowCount(0)
		col_count = len(df.columns) - 1
		row_count = len(df.index)

		table.setSelectionBehavior(QAbstractItemView.SelectRows)
		table.setColumnCount(col_count)
		table.setHorizontalHeaderLabels(list(df.columns)[1:])
		table.setRowCount(row_count)

		for i in range(row_count):
			for j in range(col_count):
				table.setItem(i, j, QTableWidgetItem(str(df.iloc[i][j+1])))

	def cb_category_table(self, df, category):
		"""
			Callback function triggered by clicking the bar chart figure;
			it will trigger a reload of the corresponding table data
		"""
		table_widget = self._categories_table_container[category]
		self._set_category_table(table_widget, df)

	def _set_category_detail_tab(self):
		"""
			Setup category table in category tab
		"""
		category_detail_tabs = QWidget()
		category_detail_tabs.layout = QHBoxLayout()

		category_det_tabs_container = QTabWidget()
		category_det_tabs_container.setTabBar(CustomTabWidget(width=100, height=25))
		category_det_tabs_container.setTabPosition(QTabWidget.West)

		category_detail_tabs.layout.addWidget(category_det_tabs_container)

		figures = self._analysis.create_category_detail()
		for name, fig in figures.items():
			layout = self._create_category_layout(fig, name)
			category_det_tabs_container.addTab(layout, name)

		category_detail_tabs.setLayout(category_detail_tabs.layout)
		self.single_categories_container.addWidget(category_detail_tabs)


def main():
	app = QApplication(sys.argv)
	v = Visualizer()
	v.show()
	app.exec_()

if __name__ == '__main__':
	main()
