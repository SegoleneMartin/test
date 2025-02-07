import argparse
import numpy as np
import matplotlib.pyplot as plt
from loguru import logger
from pathlib import Path
import os
from collections import defaultdict
from pathlib import Path
from os.path import join as ospjoin
import pickle 
from scipy.interpolate import make_interp_spline, BSpline


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Plot')
    parser.add_argument("--use_latex", type=str2bool, default=True)
    parser.add_argument("--root", type=str)
    parser.add_argument("--action", type=str, default="benchmark_plot")
    parser.add_argument("--out_dir", type=str)
    parser.add_argument("--criterion_threshold", type=float, default=1e-6*1)
    parser.add_argument("--archs", nargs='+', type=str)
    parser.add_argument("--dataset", nargs='+', type=str)
    parser.add_argument("--shots", nargs='+', type=str)
    parser.add_argument("--ncols", type=int, default=10)
    args = parser.parse_args()
    return args


list_methods = ['PADDLE', 'TIM-GD', 'ALPHA-TIM', 'Baseline', 'BDCSPN', 'SOFT_KM', 'LaplacianShot', 'PADDLE-GD']
list_name = [r'\textsc{PADDLE}', r'\textsc{TIM}', r'$\alpha$-\textsc{TIM}',
             'Baseline', r'\textsc{BDCSPN}', r'\textsc{Soft K-Means}', 'LaplacianShot', r'\textsc{PGD}']
markers = ["^", ".", "v", "1", "p", "*", "X", "d", "P", "<", ">"]
colors = ["#f02d22",
"#90813d",
"#8463cc",
"#b2b03c",
"#c361aa",
"#57ab67",
"#6691ce",
"#57ab67"]
pretty = defaultdict(str)
pretty['mini'] = r"\textit{mini}-ImageNet"
pretty['tiered'] = r"\textit{tiered}-ImageNet"

pretty["resnet18"] = "ResNet 18"
pretty["wideres"] = "WRN 28-10"

blue = '#2CBDFE'
pink = '#F3A0F2'


def moving_average(x):
    return x - x[0] + 1e-3
    # return np.convolve(x, np.ones(w), 'valid') / w


def convergence_plot(args):
    for i, dataset in enumerate(args.dataset):
        for j, arch in enumerate(args.archs):
            for k, shot in enumerate(args.shots):
                folder = ospjoin(args.root)
                _ = plt.Figure(figsize=(1, 1), dpi=300)
                ax = plt.gca()
                methods = [x[:-4] for x in os.listdir(folder)]
                logger.info(methods)
                for method in methods:
                    method_index = list_methods.index(method)
                    name_file = ospjoin(folder, f'{method}.txt')
                    if os.path.isfile(name_file) == True:
                        x, y = np.loadtxt(name_file)
                        x = np.cumsum(x)
                        criterion_defined = True
                    else:
                        logger.warning(f"Criterion not defined for {method}")
                        criterion_defined = False
                        break

                    # Criterion axis 
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)

                    msg = [str(method)]
                    if criterion_defined:
                        index_convergence = np.where(y < args.criterion_threshold)[0]
                        if len(index_convergence):
                            convergence = True
                            index_convergence = index_convergence[0]
                            time_to_convergence = x[index_convergence]
                            msg.append(f"Time to convergence = {time_to_convergence}")
                        else:
                            convergence = False
                    
                    logger.info('\t'.join(msg))

                    if criterion_defined:
                        if convergence == True:
                            n = index_convergence 
                        else:
                            if method=='ALPHA-TIM':
                                n = 6000
                            else:
                                n = 300
                        x = moving_average(x)
                        # ax.plot(y[:n],
                        #         label=list_name[method_index],
                        #         color=colors[method_index],
                        #         marker=markers[method_index],
                        #         markersize=10,
                        #         linewidth=3,
                        #         markevery=100)
                
                        ax.plot(x[:n], y[:n],
                                label=list_name[method_index],
                                color=colors[method_index],
                                linewidth=3)


                    # ax.fill_between(x, criterion['mean'] - criterion['std'], 
                    #                 criterion['mean'] + criterion['std'],
                    #                 color=colors[method_index], alpha=0.4)
                    ax.set_ylabel(r"$\| \boldsymbol{W}^{(\ell+1)} - \boldsymbol{W}^{(\ell)} \|^2$")
                    ax.set_yscale('log')
                    ax.set_xscale('log')
                    ax.set_xlabel("Elapsed time (s)")
                    # ax.set_xlabel("Iterations")
                    # ax.set_ylim(7e-8, 1e-1)


                    # color = pink
                    # if 'GD' in method:
                    #     logger.info(acc['mean'])
                    #     ax2 = ax.twinx()  # instantiate a second axes that shares the same x-axis
                    #     ax2.set_ylabel('Accuracy', color=pink)  # we already handled the x-label with ax1
                    #     ax2.plot(x, acc['mean'],
                    #              label=list_name[method_index],
                    #              color=color)
                    #     # ax2.fill_between(x, acc['mean'] - acc['std'], 
                    #     #                  acc['mean'] + acc['std'],
                    #     #                  color=color, alpha=0.4)
                    #     ax2.tick_params(axis='y', labelcolor=color)
                os.makedirs(args.out_dir, exist_ok=True)
                outfilename = ospjoin(args.out_dir,
                                      f"convergence_{dataset}_{arch}_{shot}.pdf")
                handles, labels = ax.get_legend_handles_labels()
                by_label = dict(zip(labels, handles))
                plt.legend(by_label.values(), by_label.keys(),
                           loc="center",
                           bbox_to_anchor=[1.3, 0.5],  # bottom-right
                           ncol=1,
                           frameon=False)
                plt.savefig(outfilename, bbox_inches="tight")
                logger.info(f"Saved plot at {outfilename}")


def benchmark_plot(args):
    n_dataset = len(args.dataset)
    n_archs = len(args.archs)
    assert n_dataset and n_archs
    if len(args.shots) == 'None': # for inatural
        args.shots = [1]
    fig, axes = plt.subplots(figsize=(8 * len(args.shots), 6 * n_dataset * n_archs),
                             ncols=len(args.shots),
                             nrows=n_dataset * n_archs,
                             dpi=300,
                             sharex=True,
                             )
    for i, dataset in enumerate(args.dataset):
        for j, arch in enumerate(args.archs):
            folder = Path(args.root) / dataset / arch
            min_ = 100.0
            max_ = 0.
            for k, shot in enumerate(args.shots):
                if isinstance(axes, np.ndarray):
                    if n_dataset * n_archs > 1:
                        ax = axes[i * n_archs + j, k]
                    else:
                        ax = axes[k]
                else:
                    ax = axes
                ax.spines["right"].set_visible(False)
                ax.spines["top"].set_visible(False)
                for method_index, method in enumerate(list_methods):
                    file_path = folder / f'{method}.txt'
                    if file_path.exists():
                        logger.warning(file_path)
                        tab = np.genfromtxt(file_path, dtype=float, delimiter='\t')
                        list_classes = tab[:, 0]
                        list_acc = tab[:, k + 1]
                        keep_index = list_classes <= 10
                        ax.plot(list_classes[keep_index], list_acc[keep_index],
                                marker=markers[method_index],
                                label=list_name[method_index],
                                color=colors[method_index],
                                linewidth=5 if method_index == 0 else 3.5,
                                markersize=15,
                                )
                        if max(list_acc) > max_:
                            max_ = max(list_acc)
                        if min(list_acc) < min_:
                            min_ = min(list_acc)
                # if i == 0 and j == 0:
                #     ax.set_title(rf"{shot} shots")
                if i * n_archs + j == (n_dataset * n_archs - 1):
                    ax.set_xlabel(rf'Number of effective classes $K_{{eff}}$')
                # if k == 0:
                #     ax.set_ylabel('Accuracy')
                #     ax.text(-0.5, 0.5, rf"{pretty[arch]}" + "\n" + rf"{pretty[dataset]}",
                #             rotation=90, ha='center', va='center',
                #             transform=ax.transAxes)
            ax.set_xticks(list_classes[keep_index])




    plt.tight_layout()
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(by_label.values(), by_label.keys(),
               loc="center",
               bbox_to_anchor=[0.53, 1.1],  # bottom-right
               ncol=args.ncols,
               frameon=False)
    os.makedirs(args.out_dir, exist_ok=True)
    outfilename = ospjoin(args.out_dir, f"{'-'.join(args.dataset)}_{'-'.join(args.archs)}_{'-'.join(args.shots)}.pdf")
    plt.savefig(outfilename, bbox_inches="tight")
    logger.info(f"Saved plot at {outfilename}")


if __name__ == "__main__":
    args = parse_args()
    if args.use_latex:
        logger.info("Activating latex")
        plt.rcParams.update(
            {
                "text.usetex": True,
                "font.family": "sans-serif",
                "font.sans-serif": ["Helvetica"],
                "font.size": 30
            }
        )
        plt.rc('text.latex', preamble=r'\usepackage{amsmath}')
        # \usepackage{amsmath,bm}
    if args.action == 'benchmark_plot':
        benchmark_plot(args)
    else:
        convergence_plot(args)