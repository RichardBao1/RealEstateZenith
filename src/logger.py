from datetime import date
class Logger:
    def __init__(self, prompt, log_dir='log'):
        self.log_dir = log_dir
        self.prompt = prompt

    def log(self, string, label='', level='LOG'):
        print(f'{self.prompt} ({level}) ----- {label} ----- {date.today()}: {string}')

    def as_table(self, table_dicts, label='', level='LOG'):
        """
            LOG the input as a table
        """

        headers = table_dicts[0].keys()
        h_lenghts = [len(h) for h in headers]

        # print header row
        self.log("TABLE", label=label)
        format_str = " ".join([f'{"{:<" + str(length) + "}"}' for length in h_lenghts])
        print(format_str.format(*headers))

        # print rows
        for d in table_dicts:
            v = d.values()
            print(format_str.format(*v))

    def log_f(self, string, label='', level='LOG', f_name='zumper_log.txt'):
        if ()
        with open(f'{self.log_dir}/{date.today()}_{f_name}' , 'a+') as l_f:
            l_f.write(f'{self.prompt} ({level}) ----- {label}: {string}\n')

