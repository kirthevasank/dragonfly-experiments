"""
  Synthetic experiments for optimisation.
  -- kandasamy@cs.cmu.edu
  -- kvysyara@andrew.cmu.edu
"""

#pylint: disable=no-member

import os
from argparse import Namespace
from time import time, clock

# Local
from dragonfly.opt.gp_bandit import get_all_gp_bandit_args, euclidean_specific_gp_bandit_args
from dragonfly.gp.euclidean_gp import euclidean_gp_args
from euc_opt_method_evaluator import EucOptMethodEvaluator
from dragonfly.utils.euclidean_synthetic_functions import get_syn_func_caller, get_syn_function
from dragonfly.utils.option_handler import load_options
from dragonfly.utils.reporters import get_reporter
from dragonfly.exd.worker_manager import SyntheticWorkerManager
try:
  from hyperopt import tpe, hp
except ImportError:
  pass

# Experiment Parameters ==================================================

# IS_DEBUG = True
IS_DEBUG = False

# NOISY_EVALS = True
NOISY_EVALS = False

NUM_TRIALS = 20

# STUDY_NAME = 'hartmann3'
# STUDY_NAME = 'hartmann6'
# STUDY_NAME = 'branin'
# STUDY_NAME = 'borehole'
# STUDY_NAME = 'currin_exp'
STUDY_NAME = 'park2'

# We won't be changing these much.
NUM_WORKERS = 1
MAX_CAPITAL = 200
TIME_DISTRO = 'const'
SAVE_RESULTS_DIR = 'results'

#METHODS = ['smac']
#METHODS = ['spearmint']
#METHODS = ['rand', 'pdoo', 'gpyopt', 'hyperopt', 'dragonfly']
METHODS = ['rand', 'dragonfly']

out_dir = './results'
if not os.path.exists(out_dir):
    os.makedirs(out_dir)

def get_prob_params():
  """ Returns the problem parameters. """
  prob = Namespace()
  prob.study_name = STUDY_NAME
  study_name = prob.study_name.split('-')[0]

  if IS_DEBUG:
    prob.num_trials = 3
    prob.max_capital = 10 
  else:
    prob.num_trials = NUM_TRIALS
    prob.max_capital = MAX_CAPITAL

  # Common
  prob.time_distro = TIME_DISTRO
  prob.num_workers = NUM_WORKERS
  _study_params = {'hartmann3': (0.1, 20, 2),
                   'hartmann6': (0.1, 30, 1),
                   'hartmann': (0.1, 30, 1),
                   'branin': (0.1, 20, 3),
                   'borehole': (5.0, 40, 1),
                   'park1': (0.2, 30, None),
                   'park2': (0.1, 30, None),
                  }
  _fc_noise_scale, _initial_pool_size, _fidel_dim = _study_params[study_name]
  _initial_pool_size = 0

  # noisy
  prob.noisy_evals = NOISY_EVALS
  if NOISY_EVALS:
    noise_type = 'gauss'
    noise_scale = _fc_noise_scale
  else:
    noise_type = 'no_noise'
    noise_scale = None

  # Create the function caller and worker manager
  prob.func_caller = get_syn_func_caller(STUDY_NAME, noise_type=noise_type,
                                         noise_scale=noise_scale, fidel_dim=_fidel_dim)
  _, func, prob.opt_pt, prob.opt_val, _, _, domain_bounds = \
              get_syn_function(STUDY_NAME, noise_type=noise_type, noise_scale=noise_scale)
  prob.func = lambda x: -1 * func(x) 
  prob.worker_manager = SyntheticWorkerManager(prob.num_workers,
                                               time_distro='caller_eval_cost')
  prob.save_file_prefix = prob.study_name + ('-debug' if IS_DEBUG else '')
  prob.methods = METHODS
  prob.save_results_dir = SAVE_RESULTS_DIR
  prob.reporter = get_reporter('default')

  # evaluation options
  prob.evaluation_options = Namespace(prev_eval_points='None',
                                      initial_pool_size=_initial_pool_size)
  return prob


def get_method_options(prob, capital_type):
  """ Returns a dictionary of method options. """
  methods = prob.methods
  all_method_options = {}
  euc_gpb_args = get_all_gp_bandit_args(euclidean_gp_args + 
                                        euclidean_specific_gp_bandit_args)
  for meth in methods:
    curr_options = load_options(euc_gpb_args)
    # wrap up
    curr_options.capital_type = capital_type
    if meth in ['hyperopt', 'smac', 'gpyopt', 'pdoo']:
      curr_options.func = prob.func
    if meth == 'hyperopt':
      curr_options.algo = tpe.suggest
      curr_options.space = hp.uniform
    if meth == 'spearmint':
      curr_options.exp_dir = '/home/karun/boss/e1_euc/Spearmint/' + \
                             prob.study_name.split('-')[0]
      curr_options.pkg_dir = '/home/karun/Spearmint/spearmint'  
    all_method_options[meth] = curr_options

  return all_method_options


def main():
  """ Main Function. """
  prob = get_prob_params()
  method_options = get_method_options(prob, 'return_value')
  # construct evaluator
  evaluator = EucOptMethodEvaluator(study_name=prob.study_name,
                                    func_caller=prob.func_caller,
                                    worker_manager=prob.worker_manager,
                                    max_capital=prob.max_capital,
                                    methods=prob.methods,
                                    num_trials=prob.num_trials,
                                    save_dir=prob.save_results_dir,
                                    evaluation_options=prob.evaluation_options,
                                    save_file_prefix=prob.save_file_prefix,
                                    method_options=method_options,
                                    reporter=prob.reporter)
  # run trials
  start_realtime = time()
  start_cputime = clock()
  evaluator.run_trials()
  end_realtime = time()
  end_cputime = clock()
  prob.reporter.writeln('')
  prob.reporter.writeln('realtime taken: %0.6f'%(end_realtime - start_realtime))
  prob.reporter.writeln('cputime taken: %0.6f'%(end_cputime - start_cputime))


if __name__ == '__main__':
  main()
