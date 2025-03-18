# karlsson_refprot_normalization

This code was implemented by Linda Karlsson 2024-2025, and used in the article "Reference proteins to improve performance of Core 1 and Core 2 Alzheimer’s disease CSF and plasma biomarkers" by Karlsson et al. (2025). The code can be used to run linear regression models for main predictors with and without a ratio normalization (for example with Aβ40, Aβ42 or nptau in the denominator as was used in the article). 

## File description 
In Models_refprot_normalization.ipynb, the biomarkers alone versus normalized are compared pairwise using bootstrapping. The analyses can be run to either maximize the number of subjects available or restrict to only the overlap of participants with all data available for each outcome. The code is written for three outcomes: tau PET i) temporal meta-ROI and ii) cortical composites, and iii) amyloid PET composite. The result is saved as a pickle file. It will contain a list of dataframes with linear regression and bootstrap results for each outcome in the order: 

[CSF biomarkers predicting temporal tau PET, 

CSF biomarkers predicting cortical tau PET, 

CSF biomarkers predicting amyloid PET, 

plasma biomarkers predicting temporal tau PET, 

plasma biomarkers predicting cortical tau PET, 

plasma biomarkers predicting amyloid PET]

**To run this notebook**, please insert the file name of the tabular datafile with biomarkers and outcomes, and the corresponding path. Change the name of the outcome variables and the names of the CSF biomarkers, plasma biomarkers and reference proteins to their corresponding names in the data you have. 

The number of iterations during bootstrapping can be adjusted to enable faster run times, but at the expense of less sensitive p-values. 

In Plots_refprot_normalization.ipynb, two figures can be created based on the output files in Models_refprot_normalization.ipynb. The first figure contains horizontal stacked barplots, ranked by R2-score and with the added change in R2-score for a biomarker normalized compared to alone (Figure 1 in the paper). The second figure contains vertical barplots with the improvement in R2-score for each biomarker (Figure 2 in the paper).

Fns_refprot_normalization.ipynb includes functions for linear regression models, bootstrapping and biomarker comparisons. 

## Dependencies 
Code was written in Python version 3.9. Modules:

- pandas 1.4.4
- numpy 1.23.3
- matplotlib 3.5.3
- tqdm 4.64.1
- statsmodels 0.13.2
- sklearn 0.0


