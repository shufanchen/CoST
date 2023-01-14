# basic package
import os
import pandas as pd
import numpy as np
import warnings
#  necessary package
import importlib
from pyod.utils.data import evaluate_print
from pyod.models.base import BaseDetector
from pyod.models.lof import LOF
from pyod.models.hbos import HBOS
from pyod.models.iforest import IForest
from pyod.models.copod import COPOD
from pyod.models.cof import COF
from pyod.models.feature_bagging import FeatureBagging
import random
from fpr import Fpr
from pyod.utils.example import visualize
import matplotlib.pyplot as plt


def anomaly_score():
    from pyod.models.iforest import IForest

    data = pd.read_csv(r'/home/yfy/Desktop/project/AD/contrastive/CoST/training/PHM/test_20230105_131249/cost_rep100.csv', header=None)
    data = np.array(data)
    y = np.zeros(data.shape[0])
    y[956:] = 1

    clf = IForest(random_state=324, contamination=0.05, max_samples=1.)
    clf = clf.fit(data)
    y_train_pred = clf.labels_
    index = np.where(y_train_pred == 1)
    y_train_scores = clf.decision_scores_

    desc_score_indices = np.argsort(y_train_scores, kind="mergesort")[::-1]
    a_score = y_train_scores[index]

    avg = 0
    m_avg = []
    for i in range(len(a_score)):
        avg = (a_score[i] + i*avg) / (i+1)
        m_avg.append(avg)

    avg = 0
    all_avg = []
    for i in range(len(y_train_scores)):
        avg = (y_train_scores[i] + i*avg) / (i+1)
        all_avg.append(avg)

    print(1)

random.seed(0)
warnings.filterwarnings("ignore")
# anomaly_score()

# dataset and model list / dict
all_models = {'iforest': 'IForest', 'ocsvm': 'OCSVM', 'abod': 'ABOD', 'cblof': 'CBLOF', 'cof': 'COF',
              'combination': 'aom', 'copod': 'COPOD', 'ecod': 'ECOD', 'feature_bagging': 'FeatureBagging',
              'hbos': 'HBOS', 'knn': 'KNN', 'lmdd': 'LMDD', 'loda': 'LODA', 'lof': 'LOF', 'loci': 'LOCI',
              'lscp': 'LSCP', 'mad': 'MAD', 'mcd': 'MCD', 'pca': 'PCA', 'rod': 'ROD', 'sod': 'SOD',
              'sos': 'SOS', 'vae': 'VAE', 'auto_encoder_torch': 'AutoEncoder', 'so_gaal': 'SO_GAAL',
              'mo_gaal': 'MO_GAAL', 'xgbod': 'XGBOD', 'deep_svdd': 'DeepSVDD'}

dataset_list = ['xjtu1-1']
model_dict = {'suod': 'SUOD',
              # 'vae': 'VAE',
              'iforest': 'IForest', 'cof': 'COF', 'feature_bagging': 'FeatureBagging',
              'lof': 'LOF'}
# save the results

# seed for reproducible results
seed = 324
res = {}
y_score = {}
desc_score_indices={}

for dataset in dataset_list:
    '''
    la: ratio of labeled anomalies, from 0.0 to 1.0
    realistic_synthetic_mode: types of synthetic anomalies, can be local, global, dependency or cluster
    noise_type: inject data noises for testing model robustness, can be duplicated_anomalies, irrelevant_features or label_contamination
    '''

    # data = pd.read_csv(r'/home/yfy/Desktop/project/AD/contrastive/CoST/training/XJTU/test_20230102_231937/cost_rep100.csv', header=None)
    data = pd.read_csv(r'/home/yfy/Desktop/project/AD/contrastive/CoST/training/PHM/test_20230113_193500/cost_rep100.csv', header=None)
    data = np.array(data)
    y = np.zeros(data.shape[0])
    y[120:] = 1
    # xtrain = np.concatenate((data[:100], data[-100:]), axis=0)
    # ytrain = np.zeros(100)
    # ytrain[100:] = 1

    for k, v in model_dict.items():
        # model initialization
        o = importlib.import_module("pyod.models."+k)
        # clf = getattr(o, v)(random_state=seed, contamination=0.1, max_samples=1.)  #, n_estimators=25)  # iforest conta=0.38/0.24
        # clf = getattr(o, v)(n_neighbors=180, contamination=0.06)  # LOF
        clf = getattr(o, v)(contamination=0.08,
                            base_estimators=[LOF(n_neighbors=15),
                                             LOF(n_neighbors=20),
                                             # HBOS(n_bins=10), HBOS(n_bins=20), COPOD(),
                                             IForest(n_estimators=50, max_samples=1.),
                                             IForest(n_estimators=100, max_samples=1.),
                                             IForest(n_estimators=150, max_samples=1.),
                                             FeatureBagging()])

        # clf = getattr(o, v)(contamination=0.4)  # 0.08
        # training, for unsupervised models the y label will be discarded
        clf = clf.fit(data)

        # evaluation
        y_train_pred = clf.labels_
        index = np.where(y_train_pred == 1)[0]
        res[v] = index
        print('\n', v, index[0])   # the first 1/detection

        y_train_scores = clf.decision_scores_  # raw outlier scores
        y_score[v] = y_train_scores[index]

        desc_score_indices[v] = np.argsort(y_train_scores, kind="mergesort")[::-1]
        scores = y_train_scores[desc_score_indices[v]]
        # high = np.mean(scores[:20])
        # low = np.mean(scores[-20:])

        avg = 0
        all_avg = []
        for i in range(len(y_train_scores)):
            avg = (y_train_scores[i] + i * avg) / (i + 1)
            all_avg.append(avg)

        all_avg = np.array(all_avg)

        avg = 0
        m_avg = []
        for i in range(0, y_train_scores.shape[0]-9, 1):
            # avg = (y_score[v][i] + i * avg) / (i + 1)
            m_avg.append(np.mean(y_train_scores[i:i+10]))

        m_avg = np.array(m_avg)

        gap_avg = []
        gap = 10
        re = y_train_scores.shape[0] % gap
        remain = y_train_scores.shape[0] - re - gap
        for i in range(0, remain, gap):
            g = np.mean(y_train_scores[i:i+gap])
            gap_avg.append(g)

        gap_avg.append(np.mean(y_train_scores[-re:]))
        gap_avg = np.array(gap_avg)

        # m_avg = []
        # for i in index:
        #     if i <= data.shape[0]-5:
        #         m_avg.append(np.mean(y_train_scores[i-5:i+5]))
        #
        # m_avg = np.array(m_avg)


        # critic = Fpr()
        # fpr95 = critic.evaluate(y, y_train_scores)

        # y1 = all_avg[:300]
        # y1 = y_train_scores[:300]
        # x1 = range(300)
        # x1 = range(800, data.shape[0], 1)
        plt.figure()
        plt.plot(range(data.shape[0]), y_train_scores)
        # plt.plot(x1, y1)
        plt.show()

        y3 = m_avg[90:200]
        x3 = range(90, 200, 1)
        # x3 = range(1300, m_avg.shape[0], 1)
        plt.figure()
        # plt.plot(range(m_avg.shape[0]), m_avg)
        plt.plot(x3, y3)
        plt.show()

        plt.figure()
        plt.plot(range(m_avg.shape[0]), m_avg)
        plt.show()

        # y2 = gap_avg[:81]
        # x2 = range(81)
        # # x2 = range(81, gap_avg.shape[0], 1)
        # plt.figure()
        # plt.plot(range(gap_avg.shape[0]), gap_avg)
        # # plt.plot(x2, y2)
        # plt.show()

        # plt.figure()
        # plt.hist(y_train_scores, bins=10)
        # plt.show()

        # get the prediction on the test data
        # y_test_pred = clf.predict(data)  # outlier labels (0 or 1)
        # y_test_scores = clf.decision_function(data)  # outlier scores

        # evaluate and print the results


        print("On Training Data:")
        evaluate_print(k, y, y_train_scores)
        # print("\nOn Test Data:")
        # evaluate_print(k, y, y_test_scores)

        # example of the feature importance

        # feature_importance = clf.feature_importances_
        # print("Feature importance", feature_importance)

        # visualize the results
        # visualize(clf_name, X_train, y_train, X_test, y_test, y_train_pred,
        #           y_test_pred, show_figure=True, save_figure=False)

print(1)
