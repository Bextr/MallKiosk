from os import listdir, rename


all_files = listdir('store_fronts')

for file_name in all_files:
	front, back = file_name.split('-')
	unwanted, extension = back.split('.')
	new_name = front + '.' + extension
	rename('store_fronts/' + file_name, 'store_fronts/'+new_name)