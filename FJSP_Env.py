import gym
import numpy as np
from gym.utils import EzPickle
from uniform_instance import override
from updateEndTimeLB import calEndTimeLB,calEndTimeLBm
from Params import configs
from permissibleLS import permissibleLeftShift
from updateAdjMat import getActionNbghs
from copy import deepcopy
import torch
import random
import matplotlib.pyplot as plt
import time
from min_job_machine_time import min_job_mch,min_mch_job,min_job_mch1
class FJSP(gym.Env, EzPickle):
    def __init__(self,
                 n_j,
                 n_m):
        EzPickle.__init__(self)

        self.step_count = 0
        self.number_of_jobs = n_j
        self.number_of_machines = n_m
        self.number_of_tasks = self.number_of_jobs * self.number_of_machines
        # the task id for first column
        self.first_col = []
        self.last_col = []
        self.getEndTimeLB = calEndTimeLB
        self.getNghbs = getActionNbghs

    def done(self):
        if np.all(self.partial_sol_sequeence[0] >=0):
            return True
        return False

    @override
    def step(self, action,mch_a,gantt_plt=None):
        # action is a int 0 - 224 for 15x15 for example
        time1 = time.time()
        feas, rewards, dones,masks,mch_masks = [],[], [], [],[]
        mch_spaces, mchForJobSpaces = [],[]
        for i in range(self.batch_sie):
            # Initialize done for each batch item
            done = self.done()
            # redundant action makes no effect 多余的动作无效
            if action[i] not in self.partial_sol_sequeence[i]:

                # UPDATE BASIC INFO:
                row = action[i] // self.number_of_machines#取整除
                col = action[i] % self.number_of_machines#取余数
                if i == 0:
                    self.step_count += 1
                self.finished_mark[i,row, col] = 1

                self.dur_a = self.dur[i,row, col,mch_a[i]]
                #action time
                self.partial_sol_sequeence[i][np.where(self.partial_sol_sequeence[i]<0)[0][0]] = action[i]

                self.m[i][row][col]=mch_a[i]
                # UPDATE STATE:
                # permissible left shift 允许向左移动

                startTime_a, flag = permissibleLeftShift(a=action[i], mch_a=mch_a[i], durMat=self.dur_cp[i], mchMat=self.m[i],
                                                         mchsStartTimes=self.mchsStartTimes[i], opIDsOnMchs=self.opIDsOnMchs[i],mchEndTime=self.mchsEndTimes[i])
                self.flags.append(flag)
                if gantt_plt is not None:
                    try:
                        mch_array = mch_a.detach().cpu().numpy() if hasattr(mch_a, "detach") else np.asarray(mch_a)
                        mch_val = int(mch_array[i])
                    except Exception:
                        mch_val = int(mch_a[i]) if hasattr(mch_a[i], "__int__") else mch_a[i]
                    gantt_plt.gantt_plt(row, col, mch_val, startTime_a, self.dur_a,
                                    self.number_of_jobs)
                # update omega or mask
                if action[i] not in self.last_col[i]:
                    self.omega[i,action[i] // self.number_of_machines] += 1
                else:
                    self.mask[i,action[i] // self.number_of_machines] = 1

                self.temp1[i,row, col] = startTime_a + self.dur_a#完工时间

                #temp1.shape()
                self.LBs[i] = calEndTimeLB(self.temp1[i], self.input_min[i],self.input_mean[i])

                self.LBm[i] = calEndTimeLBm(self.temp1[i],self.input_min[i])


                #self.LBs为所有task最快的完工时间
                # adj matrix
                precd, succd = self.getNghbs(action[i], self.opIDsOnMchs[i])

                self.adj[i, action[i]] = 0
                self.adj[i, action[i], action[i]] = 1
                if action[i] not in self.first_col[i]:
                    self.adj[i, action[i], action[i] - 1] = 1
                self.adj[i, action[i], precd] = 1
                self.adj[i, succd, action[i]] = 1

                '''if action[i] not in self.first_col[i]:
                    self.adj[i,action[i]-1, action[i]] = 0
                self.adj[i, precd,action[i]] = 0
                self.adj[i, action[i],succd] = 0'''
                done = self.done()
                #min_job_mch(mch_time, mchsEndTimes, number_of_machines, dur, temp, first_col)
                mch_space,mchForJobSpace,mask1,mch_mask = min_job_mch(self.mch_time[i],self.job_time[i],self.mchsEndTimes[i],self.number_of_machines,self.dur_cp[i],self.temp1[i],self.omega[i],self.mask[i],done,self.mask_mch[i])

                mch_spaces.append(mch_space)
                mchForJobSpaces.append(mchForJobSpace)
                masks.append(mask1)
                mch_masks.append(mch_mask)
                #print('action_space',mchForJobSpaces,'mchspace',mch_space)

            # prepare for return
            #-------------------------------------------------------------------------------------
            '''fea = np.concatenate((self.LBs[i].reshape(-1, 2)/configs.et_normalize_coef,
                                  self.finished_mark[i].reshape(-1, 1)), axis=-1)'''
            #----------------------------------------------------------------------------------------

            '''fea = np.concatenate((self.dur[i].reshape( -1, self.number_of_machines)/configs.et_normalize_coef,
                                  self.finished_mark[i].reshape( -1, 1)), axis=-1)'''
#--------------------------------------------------------------------------------------------------------------------

            '''fea = self.LBm[i].reshape(-1, 1) / configs.et_normalize_coef'''
            fea = np.concatenate((self.LBm[i].reshape(-1, 1) / configs.et_normalize_coef,
                                  #np.expand_dims(self.job_time[i], 1).repeat(self.number_of_machines, axis=1).reshape(
                                      #self.number_of_tasks, 1)/configs.et_normalize_coef,
                                  self.finished_mark[i].reshape( -1, 1)), axis=-1)

            feas.append(fea)


            '''reward = self.mchsEndTimes[i][mch_a[i]].max()-self.up_mchendtime[i][mch_a[i]].max()-self.dur_a


            if reward < 0.00001:
                reward = 0
            self.up_mchendtime = np.copy(self.mchsEndTimes)
            for b,c in zip(self.up_mchendtime[i],range(self.number_of_machines)):
                self.up_mchendtime[i][c] = [0 if i < 0 else i for i in b]
            rewards.append(reward)'''
            reward = -(self.LBm[i].max() - self.max_endTime[i])
            if reward == 0:
                reward = configs.rewardscale
                self.posRewards[i] += reward
            rewards.append(reward)
            self.max_endTime[i] = self.LBm[i].max()

            dones.append(done)


        t2 = time.time()
        mch_masks = np.array(mch_masks)

        #print('t2',t2-t1)
        return self.adj, np.array(feas), rewards, dones, self.omega, masks,mchForJobSpaces,self.mask_mch,self.mch_time,self.job_time

    @override
    def reset(self, data):
        #data (batch_size,n_job,n_mch,n_mch)

        self.batch_sie = data.shape[0]
        
        # Handle datasets with different machine counts
        data_n_m = data.shape[2]  # Number of machines in the data
        if data_n_m != self.number_of_machines:
            print(f"WARNING: Data has {data_n_m} machines but environment is configured for {self.number_of_machines} machines")
            print(f"Adjusting environment to match data dimensions...")
            self.number_of_machines = data_n_m
            self.number_of_tasks = self.number_of_jobs * self.number_of_machines
            
        for i in range(self.batch_sie):

            first_col = np.arange(start=0, stop=self.number_of_tasks, step=1).reshape(self.number_of_jobs, -1)[:, 0]
            self.first_col.append(first_col)
        # the task id for last column
            last_col = np.arange(start=0, stop=self.number_of_tasks, step=1).reshape(self.number_of_jobs, -1)[:, -1]
            self.last_col.append(last_col)
        self.first_col = np.array(self.first_col)
        self.last_col = np.array(self.last_col)

        self.step_count = 0
        self.m = -1 * np.ones((self.batch_sie,self.number_of_jobs,self.number_of_machines), dtype=np.int32)

        self.dur = data.astype(np.single)#single单精度浮点数
        self.dur_cp = deepcopy(self.dur)
        # record action history
        self.partial_sol_sequeence = -1 * np.ones((self.batch_sie,self.number_of_jobs*self.number_of_machines),dtype=np.int32)

        self.flags = []
        self.posRewards = np.zeros(self.batch_sie)
        self.adj = []
        # initialize adj matrix
        adj_list = []
        for i in range(self.batch_sie):
            conj_nei_up_stream = np.eye(self.number_of_tasks, k=-1, dtype=np.single)
            conj_nei_low_stream = np.eye(self.number_of_tasks, k=1, dtype=np.single)
            # first column does not have upper stream conj_nei
            conj_nei_up_stream[self.first_col] = 0
            # last column does not have lower stream conj_nei
            conj_nei_low_stream[self.last_col] = 0
            self_as_nei = np.eye(self.number_of_tasks, dtype=np.single)
            adj = self_as_nei + conj_nei_up_stream
            adj_list.append(adj)
        # Convert list to numpy array first, then to tensor
        self.adj = torch.tensor(np.array(adj_list))

        '''for i in range(self.batch_sie):
            dat = torch.from_numpy(data[i].reshape(-1, self.number_of_machines)).permute(1, 0)
            adj = np.eye(self.number_of_tasks)
            conj_nei_up_stream = np.eye(self.number_of_tasks, k=-1, dtype=np.single)
            conj_nei_low_stream = np.eye(self.number_of_tasks, k=1, dtype=np.single)
            # first column does not have upper stream conj_nei
            conj_nei_up_stream[self.first_col] = 0
            # last column does not have lower stream conj_nei
            conj_nei_low_stream[self.last_col] = 0

            one = np.where(dat > 0)

            for i in range(self.number_of_machines):
                index = np.where(one[0] == i)[0]
                for j in one[1][index]:
                    for z in one[1][index]:
                        adj[j][z] = 1
            for i in range(1,self.number_of_tasks):
                adj[i][i - 1] = conj_nei_up_stream[i][i - 1]
                adj[i - 1][i] = 0
            self.adj.append(adj)

        self.adj = torch.tensor(self.adj).type(torch.float)'''


        # initialize features
        self.mask_mch = np.full(shape=(self.batch_sie, self.number_of_jobs,self.number_of_machines, self.number_of_machines), fill_value=0,
                            dtype=bool)
        input_min=[]
        input_mean=[]
        start = time.time()
        for t in range(self.batch_sie):
            min = []
            mean = []
            for i in range(self.number_of_jobs):
                dur_min = []
                dur_mean = []
                for j in range(self.number_of_machines):
                    durmch = self.dur[t][i][j][np.where(self.dur[t][i][j] > 0)]

                    self.mask_mch[t][i][j] = [1 if i <= 0 else 0 for i in self.dur_cp[t][i][j]]
                    self.dur[t][i][j] = [durmch.mean() if i <= 0 else i for i in self.dur[t][i][j]]
                    dur_min.append(durmch.min().tolist())
                    dur_mean.append(durmch.mean().tolist())
                min.append(dur_min)
                mean.append(dur_mean)
            input_min.append(min)
            input_mean.append(mean)
        end = time.time()-start

        self.input_min = np.array(input_min)
        self.input_mean =  np.array(input_mean)
        self.input_2d = np.concatenate([self.input_min.reshape((self.batch_sie,self.number_of_jobs,self.number_of_machines,1)),
                                        self.input_mean.reshape((self.batch_sie,self.number_of_jobs,self.number_of_machines,1))],-1)

        self.LBs = np.cumsum(self.input_2d,-2)
        self.LBm = np.cumsum(self.input_min,-1)

        self.initQuality = np.ones(self.batch_sie)
        for i in range(self.batch_sie):
            self.initQuality[i] = self.LBm[i].max() if not configs.init_quality_flag else 0

        self.max_endTime = self.initQuality

        self.job_time = np.zeros((self.batch_sie, self.number_of_jobs))
        self.finished_mark = np.zeros_like(self.m)
#--------------------------------------------------------------------------------------------------------------------------
        '''fea = self.LBm.reshape(self.batch_sie,-1, 1) / configs.et_normalize_coef'''
        fea = np.concatenate((self.LBm.reshape(self.batch_sie,-1, 1) / configs.et_normalize_coef
                              #,np.expand_dims(self.job_time,2).repeat(self.number_of_machines,axis=2).reshape(self.batch_sie,self.number_of_tasks,1)/ configs.et_normalize_coef
                              ,self.finished_mark.reshape(self.batch_sie,-1, 1)), axis=-1)
#--------------------------------------------------------------------------------------------------------------------------
        '''fea = self.dur.reshape(self.batch_sie, -1, self.number_of_machines)/configs.et_normalize_coef'''

        '''fea = np.concatenate((self.LBs.reshape(self.batch_sie,-1, 2)/configs.et_normalize_coef,
                                #self.dur.reshape(self.batch_sie,-1,self.number_of_machines)/configs.high,
                              # self.dur.reshape(-1, 1)/configs.high,
                              # wkr.reshape(-1, 1)/configs.wkr_normalize_coef,
                              self.finished_mark.reshape(self.batch_sie,-1, 1)), axis=-1)'''
        # initialize feasible omega
        self.omega = self.first_col.astype(np.int64)

        # initialize mask
        self.mask = np.full(shape=(self.batch_sie,self.number_of_jobs), fill_value=0, dtype=bool)

        self.mch_time = np.zeros((self.batch_sie,self.number_of_machines))
        # start time of operations on machines
        self.mchsStartTimes = -configs.high * np.ones((self.batch_sie,self.number_of_machines,self.number_of_tasks))
        self.mchsEndTimes=-configs.high * np.ones((self.batch_sie,self.number_of_machines,self.number_of_tasks))
        # Ops ID on machines
        self.opIDsOnMchs = -self.number_of_jobs * np.ones((self.batch_sie,self.number_of_machines,self.number_of_tasks), dtype=np.int32)
        self.up_mchendtime = np.zeros_like(self.mchsEndTimes)
#用number_of_jobs填充数组的形状

        self.temp1 = np.zeros((self.batch_sie,self.number_of_jobs,self.number_of_machines))
        dur = self.dur.reshape(self.batch_sie,-1,self.number_of_machines)


        self.mask_mch = self.mask_mch.reshape(self.batch_sie,-1,self.mask_mch.shape[-1])
        return self.adj, fea, self.omega, self.mask,self.mask_mch,dur,self.mch_time,self.job_time
class DFJSP_GANTT_CHART():
    def __init__(self,total_n_job,number_of_machines):
        super(DFJSP_GANTT_CHART, self).__init__()

        self.total_n_job = total_n_job
        self.number_of_machines = number_of_machines
        self.operations_data = []  # Store operation data for analysis
        self.machine_working_times = {}  # Track machine working times
        self.initialize_plt()
        
    def colour_gen(self,n):
        '''
        为工件生成随机颜色 - 改进的颜色生成
        :param n: 工件数
        :return: 颜色列表
        '''
        # 使用更清晰的颜色调色板
        base_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
        ]
        
        colours = []
        for i in range(n):
            colours.append(base_colors[i % len(base_colors)])
        return colours
        
    def initialize_plt(self):
        # 创建更大的图形以获得更好的可读性
        plt.figure(figsize=(max(12, self.total_n_job * 2), max(8, self.number_of_machines * 1.5)))
        
        # 创建机器ID列表
        y_value = list(range(1, self.number_of_machines + 1))

        # 改进的标签和字体大小
        plt.xlabel('Time', size=16, fontweight='bold')
        plt.ylabel('Machine ID', size=16, fontweight='bold')
        plt.yticks(y_value, y_value, size=14)
        plt.xticks(size=14)
        
        # 添加网格以提高可读性
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.gca().set_axisbelow(True)

    def gantt_plt(self,job, operation, mach_a, start_time, dur_a,number_of_jobs):
        '''
        改进的Gantt图绘制
        :param job: Job ID
        :param operation: Operation ID
        :param mach_a: Machine ID
        :param start_time: Start time
        :param dur_a: Processing time
        :param number_of_jobs: Number of jobs
        '''
        colors = self.colour_gen(number_of_jobs)
        
        # 存储操作数据用于分析
        self.operations_data.append({
            'job': job,
            'operation': operation,
            'machine': mach_a,
            'start_time': start_time,
            'duration': dur_a,
            'end_time': start_time + dur_a
        })
        
        # 跟踪机器工作时间
        if mach_a not in self.machine_working_times:
            self.machine_working_times[mach_a] = 0
        self.machine_working_times[mach_a] += dur_a
        
        # 绘制改进的条形图
        bar = plt.barh(mach_a + 1, dur_a, 0.6, left=start_time, 
                      color=colors[job], alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # 改进的标签显示
        if dur_a > 0.5:  # 只在条形图足够宽时显示标签
            label_text = f'J{job + 1}\nO{operation + 1}'
            plt.text(start_time + dur_a / 2, mach_a + 1, label_text, 
                    ha='center', va='center', size=10, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
        
        # 添加持续时间标签
        if dur_a > 1.0:
            plt.text(start_time + dur_a / 2, mach_a + 0.7, f'{dur_a:.1f}', 
                    ha='center', va='center', size=9, fontweight='bold', color='white')
    
    def add_machine_trajectory_plot(self):
        '''
        添加机器工作轨迹图
        '''
        if not self.operations_data:
            return
            
        # 创建子图显示机器工作轨迹
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # 主Gantt图
        colors = self.colour_gen(self.total_n_job)
        for op in self.operations_data:
            bar = ax1.barh(op['machine'] + 1, op['duration'], 0.6, 
                          left=op['start_time'], color=colors[op['job']], 
                          alpha=0.8, edgecolor='black', linewidth=0.5)
            
            if op['duration'] > 0.5:
                ax1.text(op['start_time'] + op['duration'] / 2, op['machine'] + 1, 
                        f'J{op["job"]+1}O{op["operation"]+1}', 
                        ha='center', va='center', size=9, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
        
        ax1.set_xlabel('Time', size=14, fontweight='bold')
        ax1.set_ylabel('Machine ID', size=14, fontweight='bold')
        ax1.set_title('FJSP Schedule - Gantt Chart', size=16, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_axisbelow(True)
        
        # 机器工作轨迹图
        machines = list(range(self.number_of_machines))
        working_times = [self.machine_working_times.get(m, 0) for m in machines]
        
        bars = ax2.bar(machines, working_times, color='skyblue', alpha=0.7, edgecolor='navy')
        ax2.set_xlabel('Machine ID', size=14, fontweight='bold')
        ax2.set_ylabel('Total Working Time', size=14, fontweight='bold')
        ax2.set_title('Machine Working Time Distribution', size=16, fontweight='bold')
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.set_axisbelow(True)
        
        # 添加数值标签
        for i, (bar, time) in enumerate(zip(bars, working_times)):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{time:.1f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def add_utilization_analysis(self):
        '''
        添加利用率分析图
        '''
        if not self.operations_data:
            return
            
        # 计算总时间
        max_time = max(op['end_time'] for op in self.operations_data)
        
        # 创建利用率分析
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 机器利用率条形图
        machines = list(range(self.number_of_machines))
        utilizations = []
        for m in machines:
            total_work = self.machine_working_times.get(m, 0)
            utilization = (total_work / max_time) * 100 if max_time > 0 else 0
            utilizations.append(utilization)
        
        bars = ax1.bar(machines, utilizations, color='lightcoral', alpha=0.7, edgecolor='darkred')
        ax1.set_xlabel('Machine ID', size=12, fontweight='bold')
        ax1.set_ylabel('Utilization (%)', size=12, fontweight='bold')
        ax1.set_title('Machine Utilization Analysis', size=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_axisbelow(True)
        
        # 添加利用率数值
        for i, (bar, util) in enumerate(zip(bars, utilizations)):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{util:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # 作业完成时间分析
        job_completion_times = {}
        for op in self.operations_data:
            job_id = op['job']
            if job_id not in job_completion_times:
                job_completion_times[job_id] = 0
            job_completion_times[job_id] = max(job_completion_times[job_id], op['end_time'])
        
        jobs = list(job_completion_times.keys())
        completion_times = list(job_completion_times.values())
        
        bars2 = ax2.bar(jobs, completion_times, color='lightgreen', alpha=0.7, edgecolor='darkgreen')
        ax2.set_xlabel('Job ID', size=12, fontweight='bold')
        ax2.set_ylabel('Completion Time', size=12, fontweight='bold')
        ax2.set_title('Job Completion Time Analysis', size=14, fontweight='bold')
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.set_axisbelow(True)
        
        # 添加完成时间数值
        for i, (bar, time) in enumerate(zip(bars2, completion_times)):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{time:.1f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        return fig