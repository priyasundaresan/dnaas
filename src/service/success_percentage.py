import sys, os
import datetime
import pickle
import StringIO

def get_success_hist_png(date_start, date_end):
    logfile = open('/var/www/html/dexnet-api/webcache/dnaas.log')
    date_start = datetime.datetime.strptime(date_start, '%Y-%m-%d--%H-%M-%S')
    date_end = datetime.datetime.strptime(date_end, '%Y-%m-%d--%H-%M-%S')
    
    succs = 0
    count = 0
    badlines = 0
    requests_succ = []
    requests_fail = []
    fail_ids = []
    for i, line in enumerate(logfile):
        try:
            if i % 10 == 0:
                sys.stdout.write("Line {}\r".format(i))
                sys.stdout.flush()
            line_split = line.split(' ')
            l_date = line_split[0][1:].split('-')
            l_time = line_split[1][:-1].split(':')
            l_time_s = l_time[-1].split(',')
    
            l_dtime = datetime.datetime(int(l_date[0]), int(l_date[1]), int(l_date[2]), int(l_time[0]), int(l_time[1]), int(l_time_s[0]), int(l_time_s[1]))
    
            if l_dtime < date_start or l_dtime > date_end:
                continue
    
            datas = {}
    
            for key, value in [elm.replace(",","").split(':') for elm in line_split[5:]][:-1]:
                datas[key] = value
        
            mesh_id = datas['mesh_id']
    
            if datas['endpoint'] == 'upload_mesh': 
                fname = '/var/www/html/dexnet-api/webcache/filtered_grasps/{}'.format(mesh_id)
                if os.path.isfile(fname):
                    succs += 1
                    requests_succ.append(l_dtime)
                else:
                    requests_fail.append(l_dtime)
                    fail_ids.append(mesh_id)
                count += 1
        except Exception as e:
            print e
            badlines += 1
    print("")
    
    requests_term = []
    for id, l_dtime in zip(fail_ids, requests_fail):
        fpath = '/var/www/html/dexnet-api/webcache/persistent_errors_handled/{}'.format(id)
        if not os.path.isfile(fpath):
            fpath = '/var/www/html/dexnet-api/webcache/persistent_errors/{}'.format(id)
            if not os.path.isfile(fpath):
                continue
        with open(fpath, 'r') as f:
            out = pickle.load(f)
            if out == 'Killed':
                requests_term.append(l_dtime)
    requests_fail = [itm for itm in requests_fail if itm not in requests_term]
    
    print("{}/{} success with {} killed by user ({} bad lines)".format(succs, count, len(requests_term), badlines))
    
    time_bins = []
    ctime = date_start
    while ctime < date_end:
        time_bins.append(ctime)
        ctime += datetime.timedelta(seconds=3600)
    print(time_bins)
    if True:
        import matplotlib.pyplot as plt
        from matplotlib.dates import date2num, DateFormatter
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

        fig = Figure(figsize=(16, 10))
        axes = fig.add_subplot(1,1,1)
        axes.hist([requests_succ, requests_term, requests_fail], color=['green', 'orange', 'red'], label=['success', 'user left page', 'fail'], stacked=True, bins=date2num(time_bins))
        axes.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d::%H:%M'))
        axes.set_xlabel("Time")
        axes.set_ylabel("Number of requests")
        for tick in axes.get_xticklabels():
            tick.set_rotation(90)
        axes.legend()
        fig.tight_layout()
        
        canvas = FigureCanvas(fig)
        output = StringIO.StringIO()
        canvas.print_png(output)
        return output.getvalue()
        
