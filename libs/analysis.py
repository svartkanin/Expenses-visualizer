import math
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates
import scipy.spatial as spatial


class FollowDotCursor(object):

	def _formatter(self, x, y):
		text = "Date: " + x.strftime("%Y-%m-%d")
		text += "\nAmount: %.2f" % y
		return text

	def __init__(self, ax, x, y, tolerance=5, offsets=(-20, 20)):
		self._x_values = x

		try:
			x = np.asarray(x, dtype='float')
		except (TypeError, ValueError):
			x = np.asarray(mdates.date2num(x), dtype='float')

		y = np.asarray(y, dtype='float')
		mask = ~(np.isnan(x) | np.isnan(y))
		x = x[mask]
		y = y[mask]

		self._points = np.column_stack((x, y))
		self.offsets = offsets  # arrow offset; drawing of arrow from point x|y to offset
		y = y[np.abs(y-y.mean()) <= 3*y.std()]
		self.scale = x.ptp()
		self.scale = y.ptp() / self.scale if self.scale else 1
		self.tree = spatial.cKDTree(self.scaled(self._points))
		# self.tolerance = tolerance
		self.ax = ax
		self.fig = ax.figure
		self.ax.xaxis.set_label_position('top')
		self.dot = ax.scatter([x.min()], [y.min()], s=130, color='green', alpha=0.7)
		self.annotation = self.setup_annotation()
		# plt.connect('motion_notify_event', self)
		self.cid = self.fig.canvas.mpl_connect('motion_notify_event', self)

	def scaled(self, points):
		points = np.asarray(points)
		return points * (self.scale, 1)

	def __call__(self, event):
		ax = self.ax
		# event.inaxes is always the current axis. If you use twinx, ax could be
		# a different axis.
		if event.inaxes == ax:
			x, y = event.xdata, event.ydata
		elif event.inaxes is None:
			return
		else:
			inv = ax.transData.inverted()
			x, y = inv.transform([(event.x, event.y)]).ravel()

		annotation = self.annotation
		x, y = self.snap(x, y)
		annotation.xy = x, y
		annotation.set_text(self._formatter(x, y))
		# self.dot.set_offsets((x, y))
		bbox = ax.viewLim
		event.canvas.draw()

	def setup_annotation(self):
		"""
			Draw and hide the annotation box
		"""
		return self.ax.annotate('', xy=(0, 0), ha = 'right',
		                              xytext=self.offsets, textcoords = 'offset points', va = 'bottom',
		                              bbox=dict(boxstyle='round,pad=0.75', fc='azure', alpha=1.0),
		                              arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

	def snap(self, x, y):
		"""
			Return the value in self.tree closest to x, y
		"""
		dist, idx = self.tree.query(self.scaled((x, y)), k=1, p=1)
		try:
			x_val = self._x_values[idx]
			y_val = self._points[idx]

			return x_val, y_val[1]
			# return self._points[idx]
		except IndexError:
			return self._points[0]


class Analysis:

	def __init__(self, data_handler, group_table_cb):
		self.reset_plots()    # close all open figures to avoid unnecessary memory usage
		self._data_handler = data_handler
		self._group_table_callback = group_table_cb
		self.date_time_interval = 10    # 10 days
		plt.style.use('ggplot')

		self._day_balance_cursor = None
		self._day_overview_cursor = None
		self._expense_color = 'mediumseagreen'
		self._income_color = 'orangered'

	def reset_plots(self):
		"""
			Delete all plots for redrawing
		"""
		plt.close("all")

	def _create_groups(self, data):
		groups = [[]] * len(data.keys())
		group_counter = 0

		for values in data.values():
			groups[group_counter] = list(values.values())
			group_counter += 1

		return groups

	def _autolabel(self, rects, ax, horizontal=False):
		"""
			Label bars with the numbers they represent
		"""
		for rect in rects:
			if horizontal:
				width = rect.get_width()
				text = '%d' % int(width)

				x = width + (len(text) * 800)
				y = rect.get_y() + rect.get_height() / 2. + 0.125
				ax.text(x, y, text, ha='center', va='bottom')
			else:
				h = rect.get_height()
				text = '%d' % int(h)
				ax.text(rect.get_x()+rect.get_width()/2., h*1.03, text, ha='center', va='bottom')

	def _round_up(self, x):
		"""
			Round a number to the next 100th
		"""
		return int(math.ceil(x / 100.0)) * 100

	def _get_increase_value(self, values, picky=False):
		"""
			Calculate the maximum value to be displayed and the interval
			in which the numbers should occure
		"""
		max_val = max(values)
		new_max_val = max_val + (max_val * 3 / 5.0)

		if not picky:
			increase = self._round_up(new_max_val/8.)
		else:
			increase = self._round_up(max_val/20.)
			new_max_val = max_val + (max_val * 1./10)

		if increase == 0:
			increase = 1
		if new_max_val == 0:
			new_max_val = 1

		return new_max_val, increase

	def _get_colors(self, num):
		"""
			Retrieve a color spectrum with num colors
		"""
		cm = plt.cm.get_cmap('seismic')
		return [cm(1. * i / num) for i in range(num)]

	def _create_category_bar_charts(self, data):
		"""
			Create all category bar charts
		"""
		# the legend labels for each single bar
		bar_legend_labels_date = list(data.keys())
		category_aliases = self._data_handler.get_category_aliases(empty=False)
		# the x locations for tshe category
		x_location_categories = np.arange(1)
		bar_width = 0.05

		# categorize the data and build the groups to be displayed
		categorized_groups = self._create_groups(data)
		# get the color spectrum for the single bars
		colors = self._get_colors(len(bar_legend_labels_date))

		figures = OrderedDict()
		self._categorized_barlist = OrderedDict()

		for j in range(len(category_aliases)):
			fig = plt.figure()
			ax = fig.add_subplot(111)

			group_blocks = []
			x_location = 0
			displayed_values = []
			for i in range(len(categorized_groups)):
				if categorized_groups[i]:
					val = categorized_groups[i][j]
					rect = ax.bar(x_location_categories + x_location, [val], bar_width, color=colors[i], picker=5)
					group_blocks.append(rect)
					x_location += bar_width
					displayed_values.append(val)

			single_block = OrderedDict()
			for bar, l in zip(group_blocks, bar_legend_labels_date):
				single_block[bar] = l

			# remember the generated bar charts to be able to handle a
			# click event later to load the correct data
			self._categorized_barlist[category_aliases[j]] = single_block
			# calculate the maximum display value and the interval
			max_val, increase = self._get_increase_value(displayed_values)
			# set the y-axis label values
			ax.set_yticks(np.arange(0, max_val, increase))
			# don't show any x-axis labels
			ax.set_xticks([])

			# shrink current axis so that the legend can be displayed without
			# overlapping the bar charts
			box = ax.get_position()
			ax.set_position([box.x0, box.y0, box.width*0.8, box.height])
			# put a legend to the right of the current axis
			ax.legend(([x[0] for x in group_blocks]), bar_legend_labels_date, fontsize='small', bbox_to_anchor=(1.4, 1))

			# put the actual numbers on top of the charts
			for rec in group_blocks:
				self._autolabel(rec, ax)

			figures[category_aliases[j]] = fig

		return figures

	def _create_overall_bar_chart(self, fig):
		"""
			Create the overall bar chart
		"""
		# get the income and expenses and calculate the differnce which is displayed as well
		income, expenses = self._data_handler.get_total_in_out()
		diff = income - expenses

		labels = ('Income', 'Expense', 'Difference')
		bar_values = [income, expenses, abs(diff)]
		indexes = np.arange(len(labels))
		bar_width = 0.5

		ax = fig.add_subplot(111)
		barlist = ax.barh(indexes, bar_values, bar_width, align='edge', picker=5)

		# set the colors for the income/expense
		# the color for the difference depends on if it's a negative or positive value
		barlist[0].set_color(self._expense_color)
		barlist[1].set_color(self._income_color)
		if diff > 0:
			barlist[2].set_color(self._expense_color)
		else:
			barlist[2].set_color(self._income_color)

		# set y-axis label index
		indexes = indexes + 0.25
		ax.set_yticks(indexes)
		# set y-axis label values
		ax.set_yticklabels(labels, fontsize=15)
		# labels read top-to-bottom
		ax.invert_yaxis()
		# set x-axis values and range
		ax.set_xticks(np.arange(0, max(expenses, income) + 30000, 10000))

		self._autolabel(barlist, ax, horizontal=True)

	def _create_month_bar_chart(self, fig):
		"""
			Create the per month overview bar chart
		"""
		data = self._data_handler.get_total_month()

		# set the income and expense for each month to be displayed
		expenses, income = [], []
		for key, values in data.items():
			income.append(values[0])
			expenses.append(values[1])

		groups = [expenses, income]
		x_label_months = np.arange(len(data.keys()))
		bar_width = 0.35
		colors = [self._income_color, self._expense_color]

		ax = fig.add_subplot(111)

		bar_groups = []
		x_location = 0
		for i in range(len(groups)):
			rect = ax.bar(x_label_months + x_location, groups[i], bar_width, color=colors[i], picker=10)
			bar_groups.append(rect)
			x_location += bar_width

		# set location of x labels
		ax.set_xticks(x_label_months + bar_width)
		# set values of x labels
		ax.set_xticklabels((data.keys()))

		# calculate the max value and interval of the y-axis values
		max_val, increase = self._get_increase_value([max(groups[0]), max(groups[1])])
		# set the y-axis values
		ax.set_yticks(np.arange(0, max_val, increase))

		# specify the legend for the single bars
		bar_labels = ["Expense", "Income"]
		ax.legend(([x[0] for x in bar_groups]), bar_labels, fontsize='small')

		# put the actual numbers on top of the bars
		for rec in bar_groups:
			self._autolabel(rec, ax)

	def _day_chart_creator(self, fig, data, date_format):
		"""
			Line chart creator for the day figures
		"""
		# the x values represent the days and the y values the amount of expenses
		x = list(data.keys())
		y = list(data.values())

		ax = fig.add_subplot(111)
		ax.xaxis_date()
		ax.plot(x, y, marker='o')

		max_val, increase = self._get_increase_value(y, picky=True)
		ax.set_yticks(np.arange(0, max_val, increase))
		ax.xaxis.set_major_locator(mdates.DayLocator(interval=self.date_time_interval))
		ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))  # formatting of the ticks

		fig.autofmt_xdate()
		canvas = FigureCanvas(fig)
		cursor = FollowDotCursor(ax, x, y, tolerance=20)
		return canvas, cursor

	def _cb_on_category_pick(self, event):
		"""
			Callback function for handling single bar chart selections
		"""
		rect = event.artist
		for category, single_group in self._categorized_barlist.items():
			for bars, date in single_group.items():
				for bar in bars:
					if rect == bar:
						df = self._data_handler.get_categorized_data_sets(date, category)
						self._group_table_callback(df, category)

	def create_overall_overview(self):
		"""
			Create overall overview figure
		"""
		fig = plt.figure()
		self._create_overall_bar_chart(fig)
		canvas = FigureCanvas(fig)
		return canvas

	def create_monthly_overview(self):
		"""
			Create month overview figure
		"""
		fig = plt.figure()

		self._create_month_bar_chart(fig)
		canvas = FigureCanvas(fig)
		return canvas

	def create_category_detail(self):
		"""
			Create all category figures
		"""
		details = self._data_handler.get_calculated_categories()
		figures = self._create_category_bar_charts(details)

		for key, value in figures.items():
			canvas = FigureCanvas(value)
			canvas.mpl_connect('pick_event', self._cb_on_category_pick)
			figures[key] = canvas
		return figures

	def create_day_overview(self):
		"""
			Create the day overview figure
		"""
		fig = plt.figure()
		data, date_format = self._data_handler.get_total_day()
		canvas, cursor = self._day_chart_creator(fig, data, date_format)
		self._day_overview_cursor = cursor
		return canvas

	def create_day_balance(self):
		"""
			Create the day balance figure
		"""
		fig = plt.figure()
		data, date_format = self._data_handler.get_days_balance()
		canvas, cursor = self._day_chart_creator(fig, data, date_format)
		self._day_balance_cursor = cursor
		return canvas
