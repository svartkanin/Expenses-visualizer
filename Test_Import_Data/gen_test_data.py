# generate test data
import calendar
import random
import time
import datetime

TEST_DESCR = [
'Transaction 170426 Farmacy',
'Transaction 170426 Supermarket',
'Transaction 170426 Mini Market',
'Transaction 170425 SUSHI',
'Transaction 170425 Cafe',
'Transaction 170424 Bistro',
'Transaction 170425 Hospital',
'Transaction 170424 Gas station 1',
'Transaction 170423 Gas station 2',
'Transaction 170421 Newspaper',
'Transaction 170420 Rent',
'Transaction 170421 SUBWAY',
'Transaction 170422 Train station',
'Transaction 170422 Dog shelter',
'Transaction 170420 Grocery store',
'Transaction 170419 Barber']

def get_month_names(start, end):
	months = dict()
	for i in range(start, end+1):
		months[i] = calendar.month_name[i]
	return months 

def random_date(start, end):
	format = '%Y-%m-%d'
	stime = time.mktime(time.strptime(start, format))
	etime = time.mktime(time.strptime(end, format))
	ptime = stime + random.random() * (etime - stime)

	return time.strftime(format, time.localtime(ptime))

def get_first_last(month, year):
	_, num_days = calendar.monthrange(year, month)
	first_day = datetime.date(year, month, 1).strftime('%Y-%m-%d')
	last_day = datetime.date(year, month, num_days).strftime('%Y-%m-%d')
	return first_day, last_day

def get_random_row(month, year, descr=''):
	start, end = get_first_last(month, year)

	try:
		date = random_date(start, end)
	except:
		print(month)
		print(monthrange)
		raise ValueError('error')

	if not descr:
		idx = random.randint(0, len(TEST_DESCR)-1)
		try:
			descr = TEST_DESCR[idx]
		except:
			print(idx)
			raise ValueError('error')

		amount = random.uniform(-2000, -1)
	else:
		amount = random.uniform(3000, 6000)

	return date + ',' + descr + ',' + "\"{0:.2f}\"".format(amount) + ','

def gen_test_data():
	months = get_month_names(3, 10)
	suffix = '.csv'
	header = 'Date,Description,Amount,Balance\n'

	for year in ['2017']:
		for num, name in months.items():
			filename = year + '_' + name + suffix
			with open(filename, 'w') as fp:
				fp.write(header)
				for i in range(1, 10):
					row = get_random_row(num, int(year))
					if i == 1: row += '40000\n'
					else: row += '\n' 
					fp.write(row)
				row = get_random_row(num, int(year), 'Salary')
				fp.write(row)

gen_test_data()