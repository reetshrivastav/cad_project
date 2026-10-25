"""Build final report figures from retained measurements; no lab execution."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/final_report/figures'
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
NAVY='#17324D';BLUE='#2379A8';TEAL='#18837E';ORANGE='#CB6E35';GRAY='#B9C3CD'
paths=['reports/evidence/replication_v1_20261021/analysis/per_run.csv','reports/evidence/llmail_reserved_20261023/verified_summary.json','reports/evidence/llmail_short_cleaned_20261023/llmail_short_baseline_summary.json']
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=220,bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    svg=OUT/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
rows=list(csv.DictReader((ROOT/paths[0]).open()))
conditions=['direct','static','adaptive'];labels=['Direct','Static','Adaptive'];colors=[ORANGE,BLUE,TEAL]
fig,axes=plt.subplots(1,3,figsize=(12,3.6))
for ax,col,scale,title in [(axes[0],'benign_mean_http_ms',.001,'Benign mean HTTP latency (s)'),(axes[1],'observed_peak_kv_fraction',100,'Sampled peak KV occupancy (%)'),(axes[2],'peak_waiting',1,'Sampled waiting requests')]:
    data=[[float(r[col])*scale for r in rows if r['condition']==c] for c in conditions]
    means=[np.mean(d) for d in data];ax.bar(labels,means,color=colors,width=.58,alpha=.85)
    for i,values in enumerate(data):ax.scatter(i+np.linspace(-.10,.10,len(values)),values,c=NAVY,s=22,zorder=4)
    ax.set_title(title,fontsize=10,pad=12);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    for i,value in enumerate(means):
        text=f'{value:.2f}' if col!='peak_waiting' else f'{value:.2f}'
        ax.annotate(text,(i,value),xytext=(0,9),textcoords='offset points',ha='center',fontsize=9)
axes[0].set_yscale('log');axes[0].set_ylim(.1,150);axes[1].set_ylim(0,115);axes[2].set_ylim(0,15)
fig.suptitle('Controlled 256 MiB KV pool: three runs per condition',fontsize=13,color=NAVY,y=1.06)
fig.text(.5,-.03,'Bars: mean of three run summaries. Dots: individual runs. Peak occupancy is not total allocated VRAM.',ha='center',fontsize=9)
fig.tight_layout();save(fig,'gpu_repeatability')
reserved=json.loads((ROOT/paths[1]).read_text())
fig,ax=plt.subplots(figsize=(7.4,4.5))
for mode,label,color in [('pair','Pair',BLUE),('content_only','Content only',TEAL),('task_only','Task only',ORANGE)]:
    data=reserved['models'][mode];a=data['original_cutoff'];b=data['validation_selected_cutoff']
    xx=[100*(1-r['source_negative_specificity']) for r in (a,b)];yy=[100*r['source_positive_recall'] for r in (a,b)]
    ax.plot(xx,yy,'--',color=color,alpha=.65,lw=1.4,label=label)
    ax.scatter(xx[0],yy[0],marker='o',s=70,color=color);ax.scatter(xx[1],yy[1],marker='s',s=65,color=color)
ax.axvline(10,color=GRAY,lw=1.4,ls=':');ax.text(11,8,'Validation design target\n(not attained by pair/content on test)',fontsize=8,color=NAVY)
ax.set(xlim=(-3,103),ylim=(-4,105),xlabel='Source negatives flagged (%)',ylabel='Source positives flagged / recall (%)',title='Reserved short-email test: two frozen operating points')
ax.grid(alpha=.18);ax.legend(loc='center right',frameon=False)
fig.text(.5,-.01,'Circle: original cutoff 0.5. Square: validation-selected cutoff. Connecting segments are not ROC curves.',ha='center',fontsize=8)
fig.tight_layout();save(fig,'reserved_operating_points')
prep=json.loads((ROOT/paths[2]).read_text())
fig,ax=plt.subplots(figsize=(8,3.5));splits=['train','validation','test'];x=np.arange(3);bottom=np.zeros(3)
parts=[('Excluded: over 256 tokens','excluded_long_counts',GRAY),('Removed: lexical cleanup','removed_for_overlap',ORANGE),('Retained short emails','retained_counts',BLUE)]
totals=[sum(prep['eligible_short_counts'][s].values())+sum(prep['excluded_long_counts'][s].values()) for s in splits]
for label,key,color in parts:
    amounts=np.array([sum(prep[key][s].values()) for s in splits]);percent=amounts/np.array(totals)*100
    ax.bar(x,percent,bottom=bottom,label=label,color=color,width=.55)
    for i,(n,p) in enumerate(zip(amounts,percent)):
        if p>8:ax.text(i,bottom[i]+p/2,f'{int(n):,}\n({p:.1f}%)',ha='center',va='center',fontsize=9,color='white' if color==BLUE else NAVY)
    bottom+=percent
ax.set_xticks(x,['Training','Validation','Reserved test']);ax.set_ylim(0,105);ax.set_ylabel('Share of original assigned rows (%)');ax.set_title('Selective short-email coverage and cleanup')
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.14),ncol=3,frameon=False,fontsize=8);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
fig.tight_layout();save(fig,'data_selection')
fig,ax=plt.subplots(figsize=(10,5));ax.set_xlim(0,10);ax.set_ylim(0,5);ax.axis('off')
def box(x,y,w,h,text,color=BLUE):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.08',fc='#F1F5F9',ec=color,lw=1.3));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=9,color=NAVY)
def arrow(start,end,color=NAVY):ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':color,'lw':1.4})
box(.2,3.25,1.25,.8,'Client\nmessages');box(2,3.1,2,1.1,'Native ingress features\n+ CUDA/FP16 MiniLM\n+ XGBoost risk');box(4.6,3.1,1.5,1.1,'Tier decision\n+ live cache\nthresholds');box(7,3.3,2.6,.8,'vLLM / Qwen 3B\nFull or token-capped sandbox',TEAL)
arrow((1.45,3.65),(2,3.65));arrow((4,3.65),(4.6,3.65));arrow((6.1,3.65),(7,3.65))
box(4.6,1.65,1.5,.7,'Quarantine\nHTTP 403',ORANGE);arrow((5.35,3.1),(5.35,2.35),ORANGE)
box(7,1.65,2.6,.7,'vLLM /metrics\nKV occupancy in [0, 1]',TEAL);arrow((8.3,3.3),(8.3,2.35),TEAL);arrow((7,2),(6.1,3.1),TEAL)
box(.35,.2,5.7,.85,'Separate offline research: trusted task + one untrusted email\nPair / task-only / content-only heads; no serving integration',GRAY)
ax.text(7.9,.65,'Long-email windows tested offline\nDetection quality remains limited',ha='center',va='center',fontsize=10,color=ORANGE)
ax.text(.2,4.65,'Measured gateway and offline research remain separate',fontsize=14,color=NAVY,weight='bold');save(fig,'architecture')
long_path='reports/evidence/report_extension_20261024/verified_summary.json'
long=json.loads((ROOT/long_path).read_text())['long_email']
fig,axes=plt.subplots(1,2,figsize=(10,3.8));names=['First','Max','Mean'];aggregations=['first_window','max_window','mean_window'];xx=np.arange(3)
for ax,cutoff,title in [(axes[0],'original_cutoff','Original cutoff 0.5'),(axes[1],'frozen_short_validation_cutoff','Frozen short-validation cutoff')]:
    metrics=[long['models']['pair'][a][cutoff] for a in aggregations]
    recall=[r['source_positive_recall']*100 for r in metrics];flags=[(1-r['source_negative_specificity'])*100 for r in metrics]
    a=ax.bar(xx-.17,recall,width=.32,color=BLUE,label='Source positives flagged / recall')
    b=ax.bar(xx+.17,flags,width=.32,color=ORANGE,label='Source negatives flagged')
    ax.set_xticks(xx,names);ax.set_ylim(0,115);ax.set_title(title);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    for bars in (a,b):
        for bar in bars:ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f'{bar.get_height():.1f}',ha='center',fontsize=8)
axes[0].set_ylabel('Percentage of source class (%)')
fig.suptitle('Long-email pair head: full coverage increases flags, not reliable separation',fontsize=12,color=NAVY,y=1.04)
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,-.06),ncol=2,frameon=False,fontsize=9)
fig.tight_layout();save(fig,'long_email_tradeoff')
paths.append(long_path)
phase2_path='results/phase2_content_verified.json'
phase2=json.loads((ROOT/phase2_path).read_text())['cohorts']
fig,axes=plt.subplots(1,2,figsize=(10,3.8))
for ax,(name,title) in zip(axes,[('all_text_novel','All text-novel (n=2,000)'),('text_and_team_new','Reported new-team subset (n=1,429)')]):
    metrics=[phase2[name][key] for key in ('original_cutoff','validation_selected_cutoff')]
    xx=np.arange(2)
    for offset,key,label,color in [(-.18,'source_positive_recall','Source-positive recall',BLUE),(.18,'source_negative_specificity','Source-negative specificity',TEAL)]:
        bars=ax.bar(xx+offset,[100*m[key] for m in metrics],width=.34,label=label,color=color)
        for bar in bars:ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f'{bar.get_height():.1f}',ha='center',fontsize=8)
    ax.set_xticks(xx,['Original 0.5','Frozen higher']);ax.set_ylim(0,110);ax.set_title(title,fontsize=10);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
axes[0].set_ylabel('Percentage of source class (%)')
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,-.05),ncol=2,frameon=False)
fig.suptitle('Phase 2 content-only transfer: fixed model and operating points',fontsize=12)
fig.tight_layout();save(fig,'phase2_transfer');paths.append(phase2_path)
old_path='results/final_validation_20261025/live_gateway_final_v2.json'
new_path='results/final_validation_20261025/live_gateway_direct_v1.json'
old=json.loads((ROOT/old_path).read_text());new=json.loads((ROOT/new_path).read_text())
fig,axes=plt.subplots(1,2,figsize=(9,3.6))
for ax,key,title in [(axes[0],'warmed_extraction','Live feature extraction'),(axes[1],'warmed_http_including_backend','HTTP including generation')]:
    bars=ax.bar(['Original encode','Opt-in direct'],[old[key]['mean_ms'],new[key]['mean_ms']],color=[GRAY,BLUE])
    ax.set_ylabel('Mean milliseconds');ax.set_title(title,fontsize=11);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    for bar in bars:ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()*1.02,f'{bar.get_height():.2f}',ha='center',fontsize=9)
    ax.set_ylim(0,max(old[key]['mean_ms'],new[key]['mean_ms'])*1.2)
fig.suptitle('Separate ten-probe smoke tests; no production tail-latency claim',fontsize=11)
fig.tight_layout();save(fig,'latency_tuning');paths.extend([old_path,new_path])
manifest={'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Offline rendering from retained measurements; no new GPU or model experiment.'}
(OUT/'figure_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built seven figures (PNG and SVG) with source manifest.')
