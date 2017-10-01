#!/usr/bin/env python
"""
This is a script to automate visualising data in a batch.
1. First, files in the specified directory are parsed. Add your extension to the tail argument (in subtract) to feed correct data.
2. Calculate statistics by specifiying whether truncated or not. Usage: -t 0 or -t 1
3. Specify the logistics of the variables you wish to plot, using the plot design module. Subsetting is done on the basis of feed. Currently only supports heatmaps and lmplots.
4. Use -u 0, 1, 2 for unbounded, bounded and periodic arena-specs 
5. Use -l to specify prefix for time limit-specs (deprecated)
6. Use -p for the path where .dat files are stored (Make sure this ends with a slash)
7. Use -c = 0 or 1 to specify whether comm_data exists 
author: katanachan
email: Aishwarya Unnikrishnan <shwarya.unnikrishnan@gmail.com>
"""
print (__doc__)

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import argparse
import glob
import os
from itertools import groupby, chain
import scipy.stats as st
import scipy.special as sc
import copy
from scipy.optimize import curve_fit
import matplotlib.backends.backend_pdf

hola=[]
pdf = matplotlib.backends.backend_pdf.PdfPages("output.pdf")

class Weib(st.rv_continuous):
    def __init__(self,lower_bound=0):
        st.rv_continuous.__init__(self,a=lower_bound)
    def cdf(self,x,alpha,gamma):
        return 1 - np.exp(-np.power(x/alpha,gamma))
class Exp(st.rv_continuous):
    def __init__(self,lower_bound=0):
        st.rv_continuous.__init__(self,a=lower_bound)
    def cdf(self,x,lamda):
        return 1 - np.exp(-lamda*x)
def correct_index(f):
	if round(f)!=float(int(f)):
		if round(f)==float(int(f)+1):
			return int(f)+1
		elif round(f)==float(int(f)-1):
			return int(f)-1
	else:
		return int(f)




def aggregate_stats(data,truncated=1):
    data=pd.DataFrame(data)
    #data.to_csv('checkthis.csv')
    data=np.asarray(data)
    ## Bias 0, Alpha 1, Rho 2, Population 3, Convergence Bool 4, Convergence Time 5, Relative Convergence 6,
    ## PhiC 7, Ratio of Agents with Info 8, 9 onwards is first times of passage
    ind=np.lexsort((data[:,3],data[:,2], data[:,1]))
    data=data[ind]
    dataset=[]
    swarms=np.unique(data[:,3],return_counts=False)
    swarms=map(int,swarms)
    
    for config in range(int(data.shape[0]/len(swarms))):
        time_list=[]
        for swarm in range(len(swarms)):
            time_list.append(data[config*len(swarms)+swarm,9:9+100*swarms[swarm]])
        dataset.append(data[config*len(swarms)+swarm,:3].tolist()+list(chain.from_iterable(time_list)))
    dataset=np.asarray(dataset)
    time_list=[]
    for sample in range(dataset.shape[0]):
        censored=np.sum(np.isnan(dataset[sample,3:]))
        if censored==(dataset.shape[1]-3):
            for swarm in range(len(swarms)):
                time_list.append(data[len(swarms)*sample+swarm,:9].tolist()+[np.nan,np.nan])
        elif censored==0:
            for swarm in range(len(swarms)):
                time_list.append(data[len(swarms)*sample+swarm,:9].tolist()+[np.mean(dataset[sample,3:]),np.mean(dataset[sample,3:])])
        else:
            subset=dataset[sample,3:]
            subset=subset[np.argsort(subset)]
            uncensored=subset.size

            subset=subset[:-censored]
            n_est=np.asarray(range(0,subset.size))[::-1] + float(censored)
            RT_sync=[]
            for i in range(n_est.size):
                if len(RT_sync)==0:
                    RT_sync.append((n_est[i]-1)/n_est[i])
                else:
                    RT_sync.append(RT_sync[-1]*((n_est[i]-1)/n_est[i]))
            F=1-np.asarray(RT_sync).reshape(-1,1)
            exponential=Exp()
            weibull=Weib()
            popt_exponential,_= curve_fit(exponential.cdf,xdata=subset,ydata=np.squeeze(F),bounds=(-1000,1000),method='trf')
            popt_weibull,_= curve_fit(weibull.cdf,xdata=subset,ydata=np.squeeze(F),bounds=(0,[750000,10]),method='trf')
            
            #fig=plt.figure()
            #y_exp=exponential.cdf(subset,popt_exponential[0])
            #y_weib=weibull.cdf(subset,popt_weibull[0],popt_weibull[1])
            #error_exp= np.power(y_exp-np.squeeze(F),2)
            #error_weib=np.power(y_weib-np.squeeze(F),2)
            #plt.plot(subset,y_exp,'g',linewidth=5,label="Exponential Distribution")
            #plt.plot(subset,y_weib,'r',linewidth=5,label="Weibull Distribution")
            #plt.plot(subset,F,'b',linewidth=5,label="K-M stats")
            #plt.legend()
            #plt.ylim(0,1)
            #label="Alpha "+str(dataset[sample,1])+" Rho "+str(dataset[sample,2])+" Time of First Passage for "+str(censored)+"/"+str(uncensored)+" censored values"
            #plt.title(label)
            #plt.xlabel("Number of time steps")
            #plt.ylabel("Synchronisation probability")
            #plt.show()
            #plt.close()
            #pdf.savefig( fig )
            #fig=plt.figure()
            #plt.plot(subset,error_exp,'r--',label="for Exponential Distribution")
            #plt.plot(subset,error_weib,'g--',label="for Weibull Distribution")
            #plt.xlabel("Number of Time Steps")
            #plt.ylabel("Mean Square Error")
            #plt.legend()
            #label="Alpha "+str(dataset[sample,1])+" Rho "+str(dataset[sample,2])+" L2 Error between Distribution and K-M Statistics for "+str(censored)+"/"+str(uncensored)+" censored values"
            #plt.title(label)
            #plt.close()
            #pdf.savefig( fig )
            for swarm in range(len(swarms)):
                time_list.append(data[len(swarms)*sample+swarm,:9].tolist()+[1./popt_exponential[0],sc.gamma(1+(1./popt_weibull[1]))*popt_weibull[0]])
    

    return np.asarray(time_list)    

def stats(p,label,truncated=1,comm_data=0):
    global hola
    convergence_array = np.array(p[:,0])
    convergence_time_array = np.ma.array(p[:,1], mask=np.logical_not(convergence_array))
    censored_conv=np.sum(np.logical_not(convergence_array))
    print "No. of cases of no convergence",censored_conv
    conv_time_array = np.ma.array(p[:,2], mask=np.logical_not(convergence_array))
    visits_ratio_array = np.ma.array(p[:,3], mask=np.logical_not(convergence_array))
    percentage_tot_agents_with_info_array = np.ma.array(p[:,4], mask=np.logical_not(convergence_array))

    first_passage_time_array=np.ma.array(np.asarray(p[:,5:]).flatten())    
    #first_passage_time_array=np.ma.array(expanded_stats(p[:,5:],label),mask=np.logical_not(convergence_array))
    #censored_pass=np.sum(np.isnan(first_passage_time_array))
    #print "No of cases of no passage",censored_pass
    
    if truncated==1:
        convergence_time_array.mask=np.ma.nomask
        conv_time_array.mask=np.ma.nomask
        visits_ratio_array.mask=np.ma.nomask
        percentage_tot_agents_with_info_array.mask=np.ma.nomask
        first_passage_time_array.mask=np.ma.nomask
        
    if censored_conv==0 or truncated==0:
        head = [np.mean(convergence_array.astype(int)), np.mean(convergence_time_array.compressed()), np.mean(conv_time_array.compressed()) , np.mean(p[:,3]), np.mean(p[:,4])]+np.ravel(first_passage_time_array.compressed()).tolist()
    else:
        dataset = np.column_stack((convergence_array,
                               convergence_time_array,
                               conv_time_array,
                               visits_ratio_array,
                               percentage_tot_agents_with_info_array))
        weibull=Weib()
        data=dataset[np.argsort(dataset[:,1])]
        n_est=np.asarray(range(0,conv_time_array.compressed().size-censored_conv))[::-1] + float(censored_conv)
        RT_sync=[]
        for i in range(n_est.size):
            if len(RT_sync)==0:
                RT_sync.append((n_est[i]-1)/n_est[i])
            else:
                RT_sync.append(RT_sync[-1]*((n_est[i]-1)/n_est[i]))
        F=1-np.asarray(RT_sync).reshape(-1,1)
        
        if censored_conv !=0:
            compute=np.concatenate((data[:-censored_conv,1:3],F),1)
                
            try:
                popt,_= curve_fit(weibull.cdf,xdata=compute[:,0].compressed(),ydata=np.squeeze(F),bounds=(0,[100000,10]),method='trf')
                y_weib=weibull.cdf(compute[:,0],popt[0],popt[1])
                Tsync2=sc.gamma(1+(1./popt[1]))*popt[0]
                
                fig=plt.figure()       
                #plt.plot(compute[:,0],ys,'r',linewidth=5,label="exponwebib fit")                
                plt.plot(compute[:,0],y_weib,'y',linewidth=5,label="curve fit")
                plt.plot(compute[:,0],F,'b',linewidth=5,label="K-M stats")
                plt.legend()
                plt.ylim(0,1)
                if comm_data==0:
                    label2="Alpha "+str(label[1])+" Rho "+str(label[2])+" Population "+str(int(label[3]))+" Time of Convergence for " + str(censored_conv)+"/100 values"
                else:
                    label2="Comm "+str(label[0])+" Alpha "+str(label[1])+" Rho "+str(label[2])+" Population "+str(int(label[3]))+" Time of Convergence for " + str(censored_conv)+"/100 values"
                plt.title(label2)
                plt.xlabel("Number of time steps")
                plt.ylabel("Synchronisation probability")
                pdf.savefig( fig )
                #plt.show()
                plt.close()

                #plt.show()
                # Uncomment top line to view the fit

                #print ("Censored",Tsync)
                print ("Censored",Tsync2)
                convergence_time_array.mask=np.logical_not(convergence_array)
                print ("Uncensored", np.mean(convergence_time_array.compressed()))
                popt,_= curve_fit(weibull.cdf,xdata=compute[:,1].compressed(),ydata=np.squeeze(F),bounds=(0,[100000,10]),method='trf')
                Tsynt2=sc.gamma(1+(1./popt[1]))*popt[0]
            except:
                Tsync2=np.nan
                Tsynt2=np.nan

        else:
            Tsync2=np.mean(convergence_time_array.compressed())
            Tsynt2=np.mean(conv_time_array.compressed())    
                     
        head = [np.mean(convergence_array.astype(int)), Tsync2, Tsynt2, np.mean(p[:,3]), np.mean(p[:,4])] + np.ravel(first_passage_time_array.compressed()).tolist()
    return head

class Variable_Dictionary:
    def __init__(self,variable_name,range_val,constant_val):
        self.name=variable_name
        self.length=range_val
        self.fixed=constant_val
        self.copied=False
        self.average=0
    def get_fixed(self):
        return self.fixed
    def get_copied(self):
        return self.copied

def plot_design(data,x,y,out,plttype,title,arena,comm_data=False,rho=None,alpha=None,size=None,comm=None,separator=False):
	## General preprocessing
    data.index=map(str,np.arange(0,data.shape[0],1))
    plttype=str(plttype)
    title=str(title)
    if arena == 0:
        graph_limit=4e4
        title+=" for Unbounded Arena"
    elif arena == 1:
        title+=" for Bounded Arena"
        graph_limit=3e3
    elif arena == 2:
        title+=" for Periodic Arena"
        graph_limit=1.5e3

    levy_alpha_range=map(str,np.linspace(1,2,6))
    crw_rho_range=map(str,np.linspace(0,0.9,7))
    pop_n_range=map(str,np.linspace(10,200,20))
    comm_rad_range=map(str,np.array([0.0125,0.1,0.2,0.25,0.5]))

    levy_alpha=Variable_Dictionary("Levy-Exponent-Alpha",levy_alpha_range,alpha)
    crw_rho=Variable_Dictionary("CRW-Exponent-Rho",crw_rho_range,rho)
    pop_n=Variable_Dictionary("Population-Size",pop_n_range,size)
    comm_rad=Variable_Dictionary("Communication-Range",comm_rad_range,comm)
    convergence_time=Variable_Dictionary("Convergence-Time",graph_limit,None)

    if comm_data==True:
        dict_variables=[levy_alpha,crw_rho,pop_n,comm_rad,convergence_time]
    else:
        dict_variables=[levy_alpha,crw_rho,pop_n,convergence_time]
    z=None
    dict_inputs=[x,y]
    ## Additionally add z?
    #data.to_csv('final_data.csv',header=False)

    for i in range(len(dict_inputs)):
        dict_input=dict_inputs[i].split('-')[0]
        for j in range(len(dict_variables)):
            if dict_input==dict_variables[j].name.split('-')[0]:
                dict_inputs[i]=copy.deepcopy(dict_variables[j])
                dict_variables[j].copied=True

    for i in range(len(dict_variables)):
        if dict_variables[i].copied==False and dict_variables[i].fixed!=None:
            z=copy.deepcopy(dict_variables[i])
            dict_inputs.append(z)
    new_flag=np.sum(np.logical_not(map(Variable_Dictionary.get_fixed,dict_variables)))
    if (not comm_data and new_flag==len(dict_variables)) or (comm_data and new_flag>=len(dict_variables)-1 and not separator):
        unused_to_average= np.where(np.logical_not(map(Variable_Dictionary.get_copied,dict_variables[0:len(dict_variables)-1])))[0]
        average_value=1
        ## Changed this line to choose between out and unused variables
        for unused in range(unused_to_average.shape[0]):
            z=copy.deepcopy(dict_variables[unused_to_average[unused]])
            average_value*=len(list(set(np.unique(data[z.name])).intersection(map(float,z.length))))
        z.average=average_value
    else:
        for i in range(len(dict_inputs)):
            if dict_inputs[i].fixed != None:
                data=data[data[dict_inputs[i].name]==dict_inputs[i].fixed]

    ## Subset
    x=copy.deepcopy(dict_inputs[0])
    y=copy.deepcopy(dict_inputs[1])
        

    if plttype=="heatmap":

	## Fill values
        if separator!=False:
            dummy=dict()
            for l in range(np.unique(data[separator].shape[0])):
                dummy[l]=np.zeros((len(y.length),len(x.length)))
            #print data.groupby(separator)
            fig,axs=plt.subplots(figsize=(16,8),nrows=2,ncols=int(np.ceil(np.unique(data[separator]).shape[0]/2.0)),gridspec_kw={"height_ratios":(1.05,1.05)})
            targets=zip(np.unique(data[separator]),axs.flatten())
            for i, (key,ax) in enumerate(targets):
                sep_data=data[data[separator]==key]
                sep_data.index=map(str,np.arange(0,sep_data.shape[0],1))
                
                for ind in range(sep_data.shape[0]):
                    bin_y=(np.asarray(np.asarray(sep_data[y.name]).copy())-float(y.length[0]))/(float(y.length[-1])-float(y.length[-2]))
                    bin_x=(np.asarray(np.asarray(sep_data[x.name]).copy())-float(x.length[0]))/(float(x.length[-1])-float(x.length[-2]))
                    ## Uncomment this to verify your data
                    bin_y=len(y.length)-bin_y-1
                    
                    # I am putting a -1 in these indices because Python2.7 seems to convert float 2.0 to int 1. Weird. Pls remove if you don't have this bug.
                    #print bin_y[ind], bin_x[ind]
                    #print "Y",correct_index(bin_y[ind]), "X",correct_index(bin_x[ind])
                    dummy[i][correct_index(bin_y[ind]),correct_index(bin_x[ind])]+=sep_data[out][ind]
                    ## A const value check:
                if z.average!=0:
                    dummy[i]/=z.average
                dummy[i]=pd.DataFrame(dummy[i])
                dummy[i].columns=x.length
                dummy[i].index=y.length[::-1]
                sns.heatmap(dummy[i],annot=True,ax=ax,fmt=".0f")
                ax.set_title(separator+'='+str(key))
                ax.set_xlabel(x.name)
                ax.set_ylabel(y.name)

        else:
            ## Make bins
            bin_y=(np.asarray(np.asarray(data[y.name]).copy())-float(y.length[0]))/(float(y.length[-1])-float(y.length[-2]))
            bin_x=(np.asarray(np.asarray(data[x.name]).copy())-float(x.length[0]))/(float(x.length[-1])-float(x.length[-2]))
            ## Uncomment this to verify your data
            #data.to_csv('final_data.csv')
            bin_y=len(y.length)-bin_y-1
            dummy = np.zeros((len(y.length),len(x.length)))
            for ind in range(data.shape[0]):
                # I am putting a -1 in these indices because Python2.7 seems to convert float 2.0 to int 1. Weird. Pls remove if you don't have this bug.
                #print bin_y[ind], bin_x[ind]
                #print "Y",correct_index(bin_y[ind]), "X",correct_index(bin_x[ind])
                dummy[correct_index(bin_y[ind]),correct_index(bin_x[ind])]+=data[out][ind]
                ## A const value check:
            if z.average!=0:
                dummy/=z.average
            dummy=pd.DataFrame(dummy)
            dummy.columns=x.length
            dummy.index=y.length[::-1]
            fig=plt.figure()
            sns.heatmap(dummy,annot=True)

        
    elif plttype=="lmplot":
        print data
        scatter_kwargs={"s":100}
        data=data[~data.isnull()]
        if separator==False:
            fig=sns.lmplot(x=x.name,y=y.name,data=data,hue=out,legend_out=False,fit_reg=False,order=2,scatter=True,markers="o",size=7,aspect=1.3,scatter_kws=scatter_kwargs)
        else:
            fig=sns.lmplot(x=x.name,y=y.name,data=data,hue=out,legend_out=False,fit_reg=False,order=2,scatter=True,markers="o",size=5,scatter_kws=scatter_kwargs,col=separator)

        plt.ylim(0,np.max(data[y.name]))
        plt.xlim(0,np.max(np.unique(data[x.name]))+np.min(np.unique(data[x.name])))

    sns.plt.xlabel(x.name)
    sns.plt.ylabel(y.name)
    sns.plt.suptitle(title)
    sns.plt.subplots_adjust(top=0.9,left=0.06,right=0.97,wspace=0.08,hspace=0.25,bottom=0.06)
    if plttype=="heatmap":
        pdf.savefig( fig , dpi=900,orientation="landscape",papertype="a0")
    elif plttype=="lmplot":
        pdf.savefig( fig.fig,dpi=900 )
    #plt.show()

def subtract(a, b,tail='.dat'):
    a="".join(a.rsplit(tail))
    return "".join(a.rsplit(b))  
def main():
    global hola
    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--truncated", help="1 or 0")
    ap.add_argument("-u", "--arena", help="0 for unbounded, 1 for bounded and 2 for periodic")
    ap.add_argument("-p", "--path", help="enter path")
    ap.add_argument("-l", "--timelimit", help="Enter unique filename prefix for time limit")
    ap.add_argument("-c", "--comm", help="Enter 1 if communication range data is present")
    args=vars(ap.parse_args())
    if args.get("truncated") is None:
        truncated=0
    else:
        truncated=int(args["truncated"])
    arena=int(args["arena"])
    path=str(args["path"])
    if args.get("comm") is None:
        comm_data=0
    else:
        comm_data=int(args["comm"])
    if args.get("timelimit") is None:
        prefix='result'
    else:
        prefix=str(args["timelimit"])
    log=[]
    for filepath in glob.glob(os.getcwd()+'/'+path+'*.dat'):
        name_labels=[]
        k=[]
        save=False
        if filepath.split('/')[-1].split('_')[0] == prefix:
            file_dict=subtract(filepath,os.getcwd()+'/'+path+prefix+'_').split('_')
            for i in range(len(file_dict)):
                #name_labels.append(str([''.join(g) for _, g in groupby(file_dict[i], str.isalpha)][0]))
                k.append(float([''.join(g) for _, g in groupby(file_dict[i], str.isalpha)][1]))
            if arena == 0 and len(k)==5:
                #name_labels=name_labels[1:]
                k=k[1:]
                save = True
            elif arena != 0 and len(k)==4:
                save = True
            if save:
                b=np.genfromtxt(filepath)
                k+=stats(b,k,truncated,comm_data)
                log.append(k)
    log=aggregate_stats(log,truncated)
    log=pd.DataFrame(log)
    if comm_data==1:
        first_label="Communication-Range"
    else:
        first_label="Bias"        
    log.columns=[first_label,"Levy-Exponent-Alpha","CRW-Exponent-Rho","Population-Size"]+["Convergence_Count","Convergence-Time","Relative Convergence Time",
                                                                                     "Ratio of Total Visits","Percentage of Total Agents with Info","First Time of Passage (Exponential)","First Time of Passage (Weibull)"]                                                                             
    #plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","First Time of Passage (Exponential)","heatmap","Average First Passage Time (Exponential) for all Populations",arena,comm_data=comm_data)
    #plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","First Time of Passage (Weibull)","heatmap","Average First Passage Time (Weibull) for all Populations",arena,comm_data=comm_data)
    
    #plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Ratio of Total Visits","heatmap","PhiC ratio of Visited to Total Agents",arena,comm_data=comm_data)
    plot_design(log,"Population-Size","Convergence-Time","CRW-Exponent-Rho","lmplot","Convergence Times for Alpha=1.4",arena,comm_data=comm_data,alpha=1.4,separator="Communication-Range")
    plot_design(log,"Communication-Range","Convergence-Time","CRW-Exponent-Rho","lmplot","Convergence Times for Alpha=1.4",arena,comm_data=comm_data,alpha=1.4,separator="Population-Size")
    plot_design(log,"Population-Size","Convergence-Time","Levy-Exponent-Alpha","lmplot","Convergence Times for Rho=0.75",arena,comm_data=comm_data,rho=0.75,separator="Communication-Range")
    plot_design(log,"Communication-Range","Convergence-Time","Levy-Exponent-Alpha","lmplot","Convergence Times for Rho=0.75",arena,comm_data=comm_data,rho=0.75,separator="Population-Size")
    
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Range 0.0125",arena,comm_data=comm_data,comm=.0125,separator="Population-Size")
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Range 0.1",arena,comm_data=comm_data,comm=.1,separator="Population-Size")    
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Range 0.2",arena,comm_data=comm_data,comm=.2,separator="Population-Size")    
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Range 0.25",arena,comm_data=comm_data,comm=.25,separator="Population-Size")    
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Range 0.5",arena,comm_data=comm_data,comm=.5,separator="Population-Size")
    
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Population 10",arena,comm_data=comm_data,size=10,separator="Communication-Range")    
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Population 20",arena,comm_data=comm_data,size=20,separator="Communication-Range")
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Population 50",arena,comm_data=comm_data,size=50,separator="Communication-Range")
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Population 100",arena,comm_data=comm_data,size=100,separator="Communication-Range")
    plot_design(log,"CRW-Exponent-Rho","Levy-Exponent-Alpha","Convergence-Time","heatmap","Total Convergence Time for Population 200",arena,comm_data=comm_data,size=200,separator="Communication-Range")
    pdf.close()


if __name__ == '__main__':
    main()
