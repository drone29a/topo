def load_data(path):
    result_file = file(path, 'r')
    lines = result_file.readlines()

    fnstats = {}
    for line in lines:
        items = [item.strip() for item in line.split(',')]
        fnstat = 
    