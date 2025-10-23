
import matplotlib.pyplot as plt

def set_wide(figsize=(12, 6), title=None, xlabel=None, ylabel=None, rotate_x=0):
    plt.figure(figsize=figsize)
    if title:
        plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    if rotate_x:
        plt.xticks(rotation=rotate_x)
    plt.tight_layout()

def savefig(path):
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()