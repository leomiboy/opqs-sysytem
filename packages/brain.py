import pandas as pd
import random

class Brain:
    """
    The Brain: Core algorithm for dual-track question selection.
    Handles difficulty mapping, anti-repeat logic, and weakness analysis.
    """
    
    # Difficulty Mapping definition
    # 難易度 levels in DB: '易', '中', '難'
    MODULE_CONFIG = {
        "達B": {"易": 5, "中": 0, "難": 0},
        "衝A": {"易": 2, "中": 3, "難": 0},
        "A++": {"易": 0, "中": 3, "難": 2},
        "自訂": {"易": 2, "中": 2, "難": 1} # Balanced default
    }

    def __init__(self, full_question_bank_df):
        self.qb_df = full_question_bank_df

    def get_questions_for_practice(self, student_id, target_module, history_df=None, n=5, mode="phase1", module_config_override=None):
        """
        Select questions based on mode.
        mode="phase1": Broad Random (Anti-Repeat) using Module Distribution.
        mode="phase2": Deep Weakness Targeting (2 Weak + 2 Normal + 1 Skilled) within Module Scope.
        module_config_override: Dict from 'Modules' sheet (Filters + Counts).
        """
        if self.qb_df.empty:
            return pd.DataFrame()

        # 1. Determine Scope & Distribution
        # Start with full QB
        scoped_df = self.qb_df.copy()
        
        # Default distribution
        dist = {"易": 2, "中": 2, "難": 1} # Fallback
        
        if module_config_override:
            # A. Apply Module Filters
            # Headers: Filter_Source, Filter_Year, Filter_Unit, Filter_Diff
            f_source = module_config_override.get('Filter_Source', 'ALL')
            f_year = module_config_override.get('Filter_Year', 'ALL')
            f_unit = module_config_override.get('Filter_Unit', 'ALL')
            f_diff = module_config_override.get('Filter_Diff', 'ALL')
            
            if f_source and f_source != "ALL":
                scoped_df = scoped_df[scoped_df['來源'].isin(f_source.split(","))]
            if f_year and f_year != "ALL":
                # Year might be int or str in DF. Ensure match.
                # User input in Sheet is "110,111".
                target_years = f_year.split(",")
                # Try converting DF year to string for matching
                scoped_df = scoped_df[scoped_df['年份'].astype(str).isin(target_years)]
            if f_unit and f_unit != "ALL":
                scoped_df = scoped_df[scoped_df['單元'].isin(f_unit.split(","))]
            if f_diff and f_diff != "ALL":
                scoped_df = scoped_df[scoped_df['難易度'].isin(f_diff.split(","))]
            
            # B. Parse Distribution (for Phase 1)
            try:
                c_easy = int(module_config_override.get('Count_Easy', 0))
                c_mid = int(module_config_override.get('Count_Mid', 0))
                c_hard = int(module_config_override.get('Count_Hard', 0))
                dist = {"易": c_easy, "中": c_mid, "難": c_hard}
            except:
                pass # Use default or previous
                
        else:
            # Legacy/Static Config
            if target_module not in self.MODULE_CONFIG:
                target_module = "達B"
            dist = self.MODULE_CONFIG[target_module]

        # 2. Add UID
        # Check if UID exists or add it. (Safety check if global DF wasn't mutated permanently in init)
        # It's better to do it on scoped_df
        scoped_df['UID'] = scoped_df['年份'].astype(str) + "_" + scoped_df['來源'].astype(str) + "_" + scoped_df['題號'].astype(str)

        # 3. Filter out history (Anti-Repeat)
        available_df = scoped_df
        if history_df is not None and not history_df.empty:
            student_history = history_df[history_df['Student_ID'] == student_id]
            done_q_ids = student_history['Question_ID'].unique()
            available_df = available_df[~available_df['UID'].isin(done_q_ids)]
            
        if available_df.empty:
            return pd.DataFrame()

        # 4. Selection Logic
        selected_dfs = []
        
        # Reset n based on dist if in Phase 1?
        # User requested "Set numbers...". If user sets 3 Easy 2 Mid, n=5.
        # If user sets 1 Easy, n=1.
        # So n should be sum of dist in Phase 1.
        if mode == "phase1":
            n = sum(dist.values())
            if n == 0: n = 5 # Safety
        
        if mode == "phase2":
            # Phase 2: Deep Weakness Targeting (Strict 2-2-1 regardless of Module Count config, but respecting Module Filter Scope)
            # Logic: 2 Weak + 2 Normal + 1 Skilled
            # We need n=5 typically.
            n = 5 
            weak_units, normal_units, skilled_units = self.analyze_weakness(student_id, history_df)
            
            # Helper to sample from units
            def sample_from_units(unit_list, count, current_selected):
                if not unit_list or count <= 0:
                    return 0
                
                # Filter pool by units
                pool = available_df[available_df['單元'].isin(unit_list)]
                
                # Exclude already selected
                if current_selected:
                    current_ids = pd.concat(current_selected)['UID']
                    pool = pool[~pool['UID'].isin(current_ids)]
                
                if pool.empty:
                    return 0
                    
                got = min(len(pool), count)
                selected_dfs.append(pool.sample(n=got))
                return got

            n -= sample_from_units(weak_units, 2, selected_dfs)
            n -= sample_from_units(normal_units, 2, selected_dfs)
            n -= sample_from_units(skilled_units, 1, selected_dfs)
        
        # Phase 1 or Remaining from Phase 2: Fill Logic
        if n > 0:
            # Filter out already selected
            current_ids = []
            if selected_dfs:
                current_ids = pd.concat(selected_dfs)['UID']
                available_df = available_df[~available_df['UID'].isin(current_ids)]
            
            # Distribution Strategy
            if mode == "phase2":
                 # In leftover phase 2, just fill random from available to meet n=5
                 # Effectively "Random Practice" for remainder
                 if not available_df.empty:
                     selected_dfs.append(available_df.sample(n=min(n, len(available_df))))
            else:
                # Phase 1: Strict Adherence to 'dist'
                # If dist says Easy=3, we try to get 3 Easy.
                for diff_level, count_needed in dist.items():
                    if count_needed <= 0: continue
                    
                    pool = available_df[available_df['難易度'] == diff_level]
                    if not pool.empty:
                        got = min(len(pool), count_needed)
                        selected_dfs.append(pool.sample(n=got))
                        # Note: We don't decrement global 'n' here strictly if we just want to follow dist.
                        # But 'n' was set to sum(dist).
                        
                # Note: If pools are empty for specific difficulties, we might return fewer than expected.
                # User might want "Generic Fill"?
                # "If I want 3 Easy and 0 Easy left, give me 3 Mid?"
                # Current requirements don't specify fallback. Strict is safer for "Module" definition.
                pass 

        if not selected_dfs:
            return pd.DataFrame()
            
        final_df = pd.concat(selected_dfs).sample(frac=1) # Shuffle
        return final_df

    def analyze_weakness(self, student_id, history_df):
        """
        Analyze student's weakness based on knowledge tags (單元).
        Returns (weak_units, normal_units, skilled_units).
        Threshold: 
           Weak:   Correct Rate < 40% (and attempts >= 1) # Lower attempts threshold to catch early weakness
           Normal: 40% <= Correct Rate <= 80%
           Skilled: Correct Rate > 80%
        """
        if history_df is None or history_df.empty:
            return [], [], []
            
        student_history = history_df[history_df['Student_ID'] == student_id]
        if student_history.empty:
            return [], [], []
            
        # 1. Prepare QB mapping
        self.qb_df['UID'] = self.qb_df['年份'].astype(str) + "_" + self.qb_df['來源'].astype(str) + "_" + self.qb_df['題號'].astype(str)
        qb_units = self.qb_df[['UID', '單元']].set_index('UID')
        
        # 2. Join
        merged = student_history.join(qb_units, on='Question_ID', how='left')
        
        # 3. Aggregation
        merged['Result_Num'] = merged['Result'].apply(lambda x: 1 if str(x).upper() in ['TRUE', '1', 'CORRECT', 'YES'] else 0)
        
        stats = merged.groupby('單元')['Result_Num'].agg(['mean', 'count'])
        
        # Filter attempts: At least 1 to matter? Or 3?
        # User implies we should categorize them. Let's use 1 to include all attempted units.
        valid_stats = stats[stats['count'] >= 1]
        
        weak_units = valid_stats[valid_stats['mean'] < 0.4].index.tolist()
        normal_units = valid_stats[(valid_stats['mean'] >= 0.4) & (valid_stats['mean'] <= 0.8)].index.tolist()
        skilled_units = valid_stats[valid_stats['mean'] > 0.8].index.tolist()
        
        return weak_units, normal_units, skilled_units 
