from scipy.ndimage.filters import gaussian_filter1d
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import json, csv, os, argparse
import scipy.stats as stats
import numpy as np
import pandas
import re

import utilities.mpl as utils
import utilities
import utilities.file


plt.style.use('classic')
utils.init(20, legend_font_size=18, tick_size=16)
set_x_sci = lambda ax_: ax_.ticklabel_format(style='sci', axis='x', scilimits=(0,4))

def proc_csv(file_path):
    if not os.path.isfile(file_path): return {}
    try:
        if os.stat(file_path).st_size==0: return {}
        ds = pandas.read_csv(file_path, header=0).to_dict('Series')
        return {key:ds[key].to_numpy() for key in ds}
    except Exception as e:
        print(f'Error reading: {file_path}', e)
        return {}

class DataRoot:
    def __init__(self, dir, label):
        self.dir = dir
        self.label = label
        path_ = lambda s_: os.path.join(_a.data_dir, dir, s_)
        self.master_data = proc_csv(path_('master_stats.csv'))
        self.worker_data = proc_csv(path_('worker_stats.csv'))
        self.collect_data = proc_csv(path_('collect_stats.csv'))
        self.args = json.load(open(path_('args.json')))

    def get_label(self):
        if _a.resub:
            dir_name = self.dir
            for pattern,repl in _a.resub:
                dir_name = re.sub(pattern,repl,dir_name)
            return dir_name
        else:
            return self.label

    def get_color(self): return None


plt_ax = utilities.Registry()

#########################
# plots using worker_data
#########################

def bandwidth_(data, ax_):
    labels = ['send', 'bcast', 'total', 'both']
    cols = ('last_send', 'last_bcast', 'TOTAL')
    def proc_arr(dd):
        send, bcast, total = (dd[key] for key in cols)
        return (send, bcast, total, send + bcast)

    pt_data = [(bb.args['num_workers'], proc_arr(bb.worker_data)) for bb in data]
    pt_data.sort(key=lambda x: x[0])
    numw, numw_lab_arrs = zip(*pt_data)
    lab_numw_arrs = list(zip(*numw_lab_arrs))
    if 0:
        proc_avg = lambda arrs: list(np.mean(arr) for arr in arrs)
        for numw_arrs,lab in zip(lab_numw_arrs,labels):
            ax_.scatter(numw, proc_avg(numw_arrs), label=lab)
        leg = 1
    else:
        proc_avg = lambda arrs: list(np.mean(arr) for arr in arrs)
        numw_arrs = lab_numw_arrs[-1]
        for x_,y_ in zip(numw,numw_arrs): plt.scatter([x_] * len(y_), y_, marker='_')
        leg = 0

    #ax_.fill_between(numw, mn, mx, color='grey', alpha='0.5')
    utils.fmt_ax(ax_, 'Number of workers', 'Average worker to master time', leg=leg)
    ax_.grid(True, which='both')
    ax_.set_xlim([min(numw)-1, max(numw)+1])

def cum_(data, ax_):
    ax_.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    y_key, x_label, y_label = 'num_samples', 'Step', 'Cumulative sum of examples'
    for root in data:
        dd = root.worker_data
        # support for old csv files only
        x_key = 'master_step' if 'master_step' in dd else 'step'
        if y_key not in dd: continue
        mul_ = 1  # aa['batch_size']
        y_val = dd[y_key]
        num_ele = int(len(y_val)*1) #_a.fraction)
        y_val = y_val[:num_ele]
        ax_.plot(dd[x_key][:num_ele], np.cumsum(y_val)*mul_, color=root.get_color(),
                               linewidth=1.5, label=root.get_label())
    utils.fmt_ax(ax_, x_label, y_label, leg=1)
    ax_.grid(True, which='both')
    set_x_sci(ax_)

@plt_ax.reg
def cumsum_vs_step(*args):
    return cum_(*args)


def hist_(data, ax_, func, x_label, binwidth=None, is_time=True, mean_line=False):
    freq_ll, bins_ll = [], []

    for root in data:
        arr = func(root)
        if arr is None: continue

        arr = arr[arr>=0]
        bins = np.arange(min(arr), max(arr) + binwidth, binwidth) - binwidth/2.
        if (len(bins))<10:
            mid_val = bins[abs(int(len(bins)/2.))]
            bins = mid_val + (np.arange(10)-4)*binwidth
        freq, bins, patches = ax_.hist(arr, bins=bins, alpha=.6, edgecolor=[1]*4, color=root.get_color(), label=root.get_label())
        freq_ll.append(freq)
        bins_ll.append(bins)

        if mean_line:
            mean_ = arr.mean()
            # min_ylim, max_ylim = ax_.get_ylim()
            clr_no_alpha = patches[0]._facecolor[:-1]
            ax_.axvline(mean_, color=clr_no_alpha, linestyle='--', linewidth=2)
            #ax_.text(mean_*1.1, max_ylim*0.9, 'Mean: {:.2f}'.format(mean_))

    if not len(freq_ll)>0: return

    def get_xlims_(freq, bins):
        avg_freq = np.max(freq)  # np.mean(freq[freq>0])
        valid = (freq > avg_freq*_a.outlier_threshold).nonzero()[0]
        return bins[valid[0]]-3*binwidth, bins[valid[-1]]+6*binwidth

    if _a.remove_hist_outliers:
        mins, maxs = zip(*[get_xlims_(*its) for its in zip(freq_ll, bins_ll)])
        xmin, xmax = min(mins), max(maxs)
        ax_.set_xlim([xmin, xmax])
    else:
        xmax = max(bins.max() for bins in bins_ll)

    if is_time: x_label = utils.set_best_time_scale(ax_, xmax, x_label)
    else: set_x_sci(ax_)
    if _a.ylog or _a.hist_ylog: ax_.set_yscale('log')
    else: ax_.set_yticks([])
    utils.fmt_ax(ax_, x_label, 'Frequency', leg=1)


wd_ = lambda key: (lambda root: root.worker_data.get(key, None))
cd_ = lambda key: (lambda root: root.collect_data.get(key, None))

@plt_ax.reg
def hist_total_samples(*args):
    return hist_(*args, cd_('total_samples'), 'Master batch size', binwidth=1, mean_line=True, is_time=False)

@plt_ax.reg
def hist_worker_count(*args):
    return hist_(*args, cd_('worker_count'), 'Number of gradients per master step', binwidth=1, mean_line=True, is_time=False)

@plt_ax.reg
def hist_wait_time(*args):
    return hist_(*args, cd_('wait_time'), 'Master waiting time for workers', binwidth=0.01, mean_line=True)

@plt_ax.reg
def hist_exit(*args):
    return hist_(*args, wd_('last_exit'), 'Time between worker iterations', binwidth=0.01)

@plt_ax.reg
def hist_send(*args):
    return hist_(*args, wd_('last_send'), 'Send worker gradients time', binwidth=0.01)

@plt_ax.reg
def hist_recv(*args):
    return hist_(*args, wd_('last_recv'), 'Receive master update time', binwidth=0.01)

@plt_ax.reg
def hist_compute_time(*args):
    return hist_(*args, wd_('compute_time'), 'Computation time', binwidth=_a.binwidth_time, mean_line=True)

@plt_ax.reg
def hist_batch_size(*args):
    return hist_(*args, wd_('num_samples'), 'Worker batch size', binwidth=_a.binwidth_batch, is_time=False, mean_line=True)

@plt_ax.reg
def hist_queued_count(*args):
    return hist_(*args, wd_('last_queued_update_count'), 'Number of queued master updates', binwidth=1, is_time=False)

@plt_ax.reg
def hist_staleness(*args):
    def c_(root):
        if 'dist_sgy' in root.args and root.args['dist_sgy']=='async':
            data = root.worker_data
            return data['master_step'] - data['worker_master_step']
        else: return None
    # 'Master step - worker\'s master step'
    return hist_(*args, c_, 'Gradient staleness', binwidth=1, is_time=False)


#########################
# plots using master_data
#########################

def plot_(data, ax_, x_key, y_key, x_label, y_label, filter=True, ysci=False):
    if x_key=='time':
        xmax = max(np.max(root.master_data[x_key]) for root in data)
        x_label = utils.set_best_time_scale(ax_, xmax, x_label)
    else:
        set_x_sci(ax_)

    if ysci: ax_.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    for root in data:
        dd = root.master_data
        num_ele = int(len(dd[y_key])*1) #_a.fraction)
        y_val = dd[y_key][:num_ele]
        if filter and _a.filter_sigma:
            y_val = gaussian_filter1d(y_val, sigma=_a.filter_sigma)
        xval = dd[x_key][:num_ele]
        if x_key=='time': xval -= min(xval) 
        ax_.plot(xval, y_val, color=root.get_color(),
                                linewidth=1.5, label=root.get_label())
    utils.fmt_ax(ax_, x_label, y_label, leg=1)
    if _a.ylog: ax_.set_yscale('log')
    ax_.grid(True, which='both')

@plt_ax.reg
def loss_vs_time(*args):
    return plot_(*args, 'time', 'loss', 'Wall clock time', 'Training loss')

@plt_ax.reg
def accuracy_vs_time(*args):
    return plot_(*args, 'time', 'accuracy', 'Wall clock time', 'Test accuracy')

@plt_ax.reg
def accuracy_vs_step(*args):
    return plot_(*args, 'step', 'accuracy', 'Step', 'Test accuracy')

@plt_ax.reg
def loss_vs_step(*args):
    return plot_(*args, 'step', 'loss', 'Step', 'Training loss')

@plt_ax.reg
def step_vs_time(*args):
    return plot_(*args, 'time', 'step', 'Wall clock time', 'Step', filter=False, ysci=True)

@plt_ax.reg
def learning_rate_vs_step(*args):
    return plot_(*args, 'step', 'learning_rate', 'Step', 'Learning rate', filter=False, ysci=True)

@plt_ax.reg
def distribution(data, ax_):
    dd = data[0].args['dist']
    xmax = max(mu+sigma*5 for mu,sigma,_ in dd)
    x = np.linspace(0, xmax, 500)
    y_ = lambda x_: sum(w*stats.norm.pdf(x_, mu, sigma) for mu,sigma,w in dd if sigma!=0)
    y = y_(x) + y_(-x)
    # if absolute value taken for negative values this is the resulting pdf
    x_label = utils.set_best_time_scale(ax_, xmax, 'Induced computation delay')
    ax_.fill_between(x, 0, y, color='tan')   # label='Expected value ~=%g'%(x@y/sum(y)))

    ymax = max(y)
    for mu,sigma,w in dd:
        if sigma==0:
            ax_.arrow(mu,0,0,ymax*1.2, head_width=0.08, head_length=0.03, linewidth=3, color='k')
            ax_.annotate(f'{w:g}', xy=(mu,ymax*1.3), ha='left')

    delta = (max(x)-min(x))*0.02
    ax_.set_xlim([min(x)-delta, max(x)+delta])
    ax_.set_ylim([0, ymax*1.5])
    ax_.set_yticks([])
    utils.fmt_ax(ax_, x_label, 'PDF', 0)


#########################
# multiple plts on figure
#########################

plt_fig = utilities.Registry()


def single_plot(plt_ax_handle):
    def inner(data, sv_):
        plt_ax_handle(data, plt.gca())
        sv_()
    return inner
for name_,hdl_ in plt_ax.items(): plt_fig.put(name_, single_plot(hdl_))

@plt_fig.reg
def loss(data, sv_):
    gs = gridspec.GridSpec(2, 1)
    loss_vs_step(data, plt.subplot(gs[0, 0]))
    loss_vs_time(data, plt.subplot(gs[1, 0]))
    sv_()

@plt_fig.reg
def master_bandwidth(data, sv_):
    bandwidth_(data, plt.gca())
    sv_()



panel_main = (loss_vs_step, loss_vs_time, hist_compute_time,
              accuracy_vs_step, accuracy_vs_time, hist_batch_size,
              cumsum_vs_step, step_vs_time, learning_rate_vs_step)
panel_hist = (hist_send, hist_recv, hist_exit, hist_staleness, hist_queued_count,
              hist_wait_time, hist_compute_time, hist_batch_size, distribution,
              hist_total_samples, hist_worker_count)
panel_all = sorted(list(set((*panel_main, *panel_hist))), key=lambda it: it.__name__)

def panel_maker(name, hdls):
    def get_hdls():
        if _a.subset is not None:
            return [plt_ax.get(val) for val in _a.subset], 'panel_subset'
        else: return hdls, name

    def panel(data, sv_):
        hdls_, name_ = get_hdls()
        axes, fig = utils.get_subplot_axes(_a, len(hdls_))
        for i, ax in enumerate(axes): hdls_[i](data, ax)
        sv_(name_)
        return hdls_

    def panel_iter(data, sv_):
        hdls_ = panel(data, sv_)
        for hdl_ in hdls_:
            plt.figure()
            hdl_(data, plt.gca())
            sv_(hdl_.__name__)

    plt_fig.put(name, panel)
    plt_fig.put(f'{name}_iter', panel_iter)

panel_maker('panel_main', panel_main)
panel_maker('panel_hist', panel_hist)
panel_maker('panel_all', panel_all)


def main():
    dirs, labels = utilities.file.filter_directories(_a, _a.data_dir)
    if not dirs: exit()
    data = [DataRoot(dir,lab) for dir,lab in zip(dirs, labels)]
    get_path = lambda name_: os.path.join(_a.data_dir, name_)
    def save_hdl(name_=_a.type):
        if _a.ylog: name_ = f'{name_}_ylog'
        plt.gcf().canvas.set_window_title(f'{_a.data_dir}: {name_}')
        utils.save_show_fig(_a, plt, get_path(name_))
    plt_fig.get(_a.type)(data, save_hdl)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_dir', default=utilities.file.resolve_data_dir_os('distributed'))

    parser.add_argument('--type', default='panel_main', choices=plt_fig.keys())
    parser.add_argument('--subset', nargs='+', choices=plt_ax.keys())

    ## histogram-related arguments
    parser.add_argument('--binwidth_time', type=float, default=0.01)
    parser.add_argument('--binwidth_batch', type=float, default=1)
    parser.add_argument('--hist_ylog', action='store_true')
    parser.add_argument('--remove_hist_outliers', action='store_true')
    parser.add_argument('--outlier_threshold', type=float, default=0.00005)

    parser.add_argument('--resub', action='append', nargs=2, metavar=('pattern','substitute'))

    parser.add_argument('--ylog', action='store_true')
    parser.add_argument('--filter_sigma', default=0, type=float)
    # parser.add_argument('--fraction', help='drop time series data after this fraction', default=1, type=float)

    utilities.file.bind_dir_filter_args(parser)
    utils.bind_subplot_args(parser, ax_size_default=[8,5])
    utils.bind_fig_save_args(parser)
    return parser.parse_args()

if __name__ == '__main__':
    _a = parse_args()
    print('[Arguments]', vars(_a))
    main()
