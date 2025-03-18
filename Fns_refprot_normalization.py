## Author: Linda Karlsson, 2024

# import packages

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import statsmodels.formula.api as smf
from tqdm import tqdm
from sklearn.metrics import r2_score
from statsmodels.stats.multitest import fdrcorrection



def create_biomarker_ratios(df,biomarkers,refprot,name2='_refprot_normalized'):
    """
    Creates ratios with a reference protein for a list of biomarkers in a dataframe, and adds a the new biomarker ratio to the dataframe.

    Inputs:
        - df (DataFrame): DataFrame including the biomarkers and reference protein.
        - biomarkers (List): List of biomarkers.
        - refprot (String): Name of reference protein.

    Outputs: 
        - df (DataFrame): Updated DataFrame, now also including the biomarker ratios.
        - biomarker_normalized (List): List of names of the new biomarker ratios.
    """
    biomarker_normalized = []
    for biomarker in biomarkers:
        name = biomarker + name2
        df[name] = df[biomarker]/df[refprot]
        biomarker_normalized.append(name)
    return df, biomarker_normalized




def compare_biomarkers(df,biomarkers,biomarkers_normalized,refprot,outcome,n_iter=1000):
    """
    Creates linear regression models for all biomarkers in biomarkers, biomarkers normalized and the reference protein. Compares biomarker ratios with bootstrapping between biomarkers and biomarkers_normalized. 

    Inputs:
        - df (DataFrame): DataFrame including the biomarkers, outcome and reference protein.
        - biomarkers (List): List of biomarkers.
        - biomarker_normalized (List): List of names of the biomarker ratios (should be in same order as biomarkers).
        - refprot (String): Name of reference protein.
        - outcome (String): Name of outcome variable in regression models.
        - n_iter (int): Number of iterations in bootstrapping. Defaults to 1000.

    Outputs: 
        - all_res (DataFrame): Dataframe with linear regression results for all biomarkers, and bootstrapped comparison between biomarkers_normalized and biomarkers.
    """
    #create linear regression models for all biomarkers
    res = test_linreg(df,biomarkers + [refprot],outcome=outcome,other=refprot)
    res_norm = test_linreg(df,biomarkers_normalized,outcome=outcome)
    
    #compare significance with bootstrapping
    diff = get_bootstrapped_diff(df,biomarkers,biomarkers_normalized,outcome=outcome,n_iter=n_iter)

    # add bootstrapped comparison
    res_norm = res_norm.merge(diff,on=['biomarker','nobs'])
    
    # save results in single dataframe
    all_res = pd.concat([res,res_norm]).reset_index(drop=True)
    
    return all_res



def get_pvalues(all_res,biomarkers_normalized,n_iter=1000):
    """
    Get P-values (raw and FDR-corrected) for all biomarkers in all_res files generated by compare_biomarkers(). 

    Inputs:
         - all_res (DataFrame): Dataframe with linear regression results for all biomarkers, and bootstrapped comparison between biomarkers_normalized and biomarkers.
        - biomarker_normalized (List): List of names of the biomarker ratios.
        - n_iter (int): Number of iterations in bootstrapping. Defaults to 1000.

    Outputs: 
        - all_res (DataFrame): Dataframe with linear regression results for all biomarkers, bootstrapped comparison between biomarkers_normalized and biomarkers and corresponding P-values (raw and FDR corrected).
    """
    pvals = []
    pvals_cor = []
    diffs = []
    for res in all_res:
        comp = res[['R2_diff']].dropna()
        for c in comp['R2_diff']:
            pval = min(len(c[c < 0])/n_iter,len(c[c > 0])/n_iter)
            pvals.append(pval)
            pvals_cor.append(max(pval,1/n_iter))
            diffs.append(c.mean())
        
    pvals_fdr = fdrcorrection(pvals_cor)[1]

    i = 0
    for res in all_res:
        adds_idx = res[res['biomarker'].isin(biomarkers_normalized)].index
        res.loc[adds_idx,'R2_difference'] = diffs[i:i+len(adds_idx)]
        res.loc[adds_idx,'P-value'] = pvals[i:i+len(adds_idx)]
        res.loc[adds_idx,'P-value FDR'] = pvals_fdr[i:i+len(adds_idx)]
        i = i + len(adds_idx)
    return all_res




def get_bootstrapped_vals(df,bms,outcome):
    """
    Get bootstrapped R2-score for a list of biomarkers. 

    Inputs:
        - df (DataFrame): DataFrame including the biomarkers and outcome.
        - bms (List): List of biomarkers.
        - outcome (String): Name of outcome variable in regression model.

    Outputs: 
        - boot_res (df): DataFrame with bootstrap results, including the n_iter R2-scores and beta_coefficients for all biomarkers.
    """
    cols = ['R2','beta','biomarker']
    boot_res = pd.DataFrame(columns=cols)
    for bm in bms:
        R2s_diff, betas_diff = bootstrap_linreg_single(df,bm,outcome=outcome)
        boot_res.loc[len(boot_res),cols] = [R2s_diff,betas_diff,bm]
    return boot_res




def test_linreg(df1,to_test,outcome,other=''):
    """
    Creates linear regression models for all biomarkers. Use 'other' to make sure only data that also has values for the reference protein is used (fair comparison between subjects).

    Inputs:
        - df1 (DataFrame): DataFrame including the biomarkers and outcome.
        - to_test (List): Biomarkers to test as predictors in linear regression models.
        - outcome (String): Name of outcome variable in regression model.
        - other (String'): Name of data that should be dropped if values are NaN for participants (e.g. the reference protein).

    Outputs: 
        - df (DataFrame): DataFrame with resulting biomarker name, R2-score, Beta-coefficient, linear regression model and number of observations.
    """
    if other != '':
        df1 = df1[df1[other].notnull()].reset_index(drop=True)
    R2s = []
    betas = []
    models = []
    nobs = []
    for test in to_test:
        model = get_linreg(df1,test,outcome)
        R2s.append(model.rsquared)
        betas.append(model.params['mp'])
        models.append(model)
        nobs.append(model.nobs)
    return pd.DataFrame({'biomarker':to_test,'R2':R2s,'Beta':betas,'model':models,'nobs':nobs})




def get_linreg(df1, main_pred,outcome):
    """
    Creates univariate linear regression model for a main predictor and outcome. Missing values are dropped and variables are standardized before applied in models. 

    Inputs:
        - df1 (DataFrame): DataFrame including the main predictor and outcome.
        - main_pred (String): Name of main predictor in regression model.
        - outcome (String): Name of outcome variable in regression model.

    Outputs: 
        - model (statsmodels.regression.linear_model.RegressionResultsWrapper): Linear regression model results.
    """
    X = df1[[main_pred,outcome]].astype(float)
    X = X.dropna()
    X_n = StandardScaler().fit_transform(X)
    X_n = pd.DataFrame(X_n, columns=X.columns)
    X_n['mp'] = X_n[main_pred]
    model = smf.ols(outcome + '~' + 'mp', data=X_n,missing='drop').fit(disp=False)
    return model



def get_bootstrapped_diff(df,biomarkers,biomarkers_normalized,outcome,n_iter):
    """
    Get bootstrapped difference in R2-score between a list of normalized and non-normalized biomarkers. 

    Inputs:
        - df (DataFrame): DataFrame including the biomarkers and outcome.
        - biomarkers (List): List of biomarkers.
        - biomarker_normalized (List): List of names of the biomarker ratios (should be in same order as biomarkers).
        - outcome (String): Name of outcome variable in regression model.
        - n_iter (int): Number of iterations in bootstrapping.

    Outputs: 
        - boot_res (df): DataFrame with bootstrap results, including the R2-difference and number of observations, for the biomarker ratio ('biomarker') compared against the biomarker alone ('compared_against').
    """
    cols = ['R2_diff','nobs','compared_against','biomarker']
    boot_res = pd.DataFrame(columns=cols)
    for main,with_ref in zip(biomarkers,biomarkers_normalized):
        R2s_diff, nobs = bootstrap_linreg(df,main,with_ref,outcome=outcome,n_iter=n_iter)
        boot_res.loc[len(boot_res),cols] = [R2s_diff,nobs,main,with_ref]
    return boot_res



def bootstrap_linreg(df,to_test1,to_test2,outcome,n_iter):
    """
    Get bootstrapped difference in R2-score between two predictors (always compare same bootstrapped subsample of data). 

    Inputs:
        - df (DataFrame): DataFrame including the predictors and outcome.
        - to_test1 (String): Name of first predictor.
        - to_test2 (String): Name of second predictor.
        - n_iter (int): Number of iterations in bootstrapping.

    Outputs: 
        - R2s (Array): Array with difference in R2-score between two models for all iterations.
        - len(df) (int): total length of DataFrame (number of observations)
    """
    R2s = []
    df = df[[to_test1,to_test2,outcome]].dropna().reset_index(drop=True)
    for n in tqdm(range(n_iter)):
        idx_train = np.random.choice(len(df), size=len(df), replace=True)
        df_boot = df.iloc[idx_train]
        model1 = get_linreg(df_boot,to_test1,outcome)
        model2 = get_linreg(df_boot,to_test2,outcome)
        R2s.append(model2.rsquared-model1.rsquared)
    
    return np.array(R2s),len(df)




def bootstrap_linreg_single(df,to_test,outcome,n_iter=1000):
    """
    Get bootstrapped R2-score for a predictor. 

    Inputs:
        - df (DataFrame): DataFrame including the predictor and outcome.
        - to_test1 (String): Name of predictor.
        - n_iter (int): Number of iterations in bootstrapping. Defaults to 1000.

    Outputs: 
        - R2s (Array): Array with n_iter R2-scores.
        - betas (Array): Array with n_iter beta-coefficients.

    """
    R2s = []
    betas = []
    df = df[[to_test,outcome]].dropna().reset_index(drop=True)
    for n in tqdm(range(n_iter)):
        idx_train = np.random.choice(len(df), size=len(df), replace=True)
        df_boot = df.iloc[idx_train]
        model = get_linreg(df_boot,to_test,outcome)
        R2s.append(model.rsquared)
        betas.append(model.params['mp'])
    return np.array(R2s),np.array(betas)




def pre_process_results_all(results_all,n_iter=1000):
    """
    Pre-process results from head-to-head comparison by adding R2 mean value and limits for confidence interval.

    Inputs:
        - results_all (List): List of DataFrames in format boot_res from get_bootstrapped_vals().
        - n_iter (int): Number of iterations in bootstrapping. Defaults to 1000.

    Outputs: 
        - results_all (List): Updated results_all file now also including R2 mean value and limits for confidence interval.

    """
    for result_all in results_all:
        for res,i,bm in zip(result_all['R2'],range(len(result_all['R2'])), result_all['biomarker']):
            res_mean = res.mean()
            res_lower = sorted(res)[int(0.05*n_iter)]
            res_upper = sorted(res)[int(0.95*n_iter)]
            result_all.loc[i,['R2_mean','R2_lower','R2_upper']] = [res_mean,res_lower,res_upper]
    return results_all


def give_color(df):
    """
    Add color specifics for dataframe with biomarker names including the biomarkers alone (dimgray) and ratios with ab40 (lightseagreen), nptau (royalblue) or ab42 (peru).

    Inputs:
        - df (DataFrame): DataFrame including the column 'name' where biomarker names are specified.

    Outputs: 
        - cols (List): List of colors for order in df['name'].
    """
    cols = []
    for bm in df['name']:
        if ('/Ab40' in bm) or ('/Aβ40' in bm):
            cols.append('lightseagreen')
        elif '/np-tau' in bm:
            cols.append('royalblue')
        elif ('/ab42' in bm) or ('/aβ42' in bm):
            cols.append('peru')
        else:
            cols.append('dimgray')
    return cols



def pre_process_result_diff(results_diff,names):
    """
    Pre-process results from linear regression differences by adding R2 mean difference and limits for confidence interval, as well as significance markers according signifiance level.

    Inputs:
        - results_diff (List): List of DataFrames in format all_res from get_pvalues().
        - names (Dict): Dictionary with names of biomarkers in data as keys and intended names in plots as values.

    Outputs: 
         - results_diff (List): List of DataFrames in same format as input but now also including biomarker plot name, R2 mean difference and limits for confidence interval, as well as significance markers according signifiance level.
    """
    
    results_diff = results_diff.dropna().reset_index(drop=True)

    for diff,name,pval_fdr,i in zip(results_diff['R2_diff'],results_diff['biomarker'],results_diff['P-value FDR'],range(len(results_diff))):
        mean_diff = diff.mean()
        lower = sorted(diff)[int(0.05*len(diff))]
        upper = sorted(diff)[int(0.95*len(diff))]
        
        if pval_fdr < 0.001:
            sig = '***'
        elif pval_fdr < 0.01:
            sig = '**'
        elif pval_fdr < 0.05:
            sig = '*'
        else:
            sig = ''
        results_diff.loc[i,['mean_diff','lower','upper','sig','name']] = [mean_diff,lower,upper,sig,names[name]]

    results_diff['color'] = give_color(results_diff)
    results_diff = results_diff.sort_values(by = 'mean_diff',ascending=False)
    return results_diff

