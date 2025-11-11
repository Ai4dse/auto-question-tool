import random
import numpy as np
from app.resources.synonyms import synonym_pairs
import itertools


DIFFICULTY_SETTINGS = {
    "easy": {"matrix_size": [3], "steps": [0], "discrete": [True]},
    "medium": {"matrix_size": [3, 4], "steps": [0, 1], "discrete": [True, False]},
    "hard": {"matrix_size": [4, 5], "steps": [1, 2], "discrete": [False]},
}

class HungarianMethodQuestion:
    def __init__(self, seed=None, difficulty="easy", mode='steps'):
        
        self.difficulty = difficulty.lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])
        
        self.seed = seed or random.randint(1, 999999)
        random.seed(self.seed)
        self.matrix_size = random.choice(config["matrix_size"])
        self.steps = random.choice(config["steps"])
        self.discrete = random.choice(config["discrete"])
        self.mode = mode

        self.pairs = random.sample(synonym_pairs, self.matrix_size)

        self.schemaA = [a for a, b in self.pairs]
        random.shuffle(self.schemaA)
        self.schemaB = [b for a, b in self.pairs]
        random.shuffle(self.schemaB)

        print('hello world')
        current_steps = -1
        while (current_steps != self.steps):
            self.path = []
            self.numbers = self.random_numbers(self.matrix_size * self.matrix_size, self.discrete, self.seed)
            res = self.hungarian_method(self.numbers, self.matrix_size)
            current_steps = res[1]['max_depth']
            #self.seed += 1
            print(f'Path: {self.path}')
        
        #self.seed = seed or random.randint(1, 999999)
        #random.seed(self.seed)
        #np.random.seed(self.seed)
        #self.addition_data = []
        #self.a = random.randint(self.min, self.max)
        #self.b = random.randint(self.min, self.max)
        #self._run_addition()

    def random_numbers(self, n, discrete=True, seed=None, low=0, high=10):
        rng = np.random.default_rng(seed)

        if discrete:
            return rng.integers(low, high + 1, size=n).tolist()
        else:
            return rng.uniform(low, high, size=n).round(1).tolist()
        
    def check_coverage(self, comb, zeros, matrix_size):
        for element in comb: 
            if element >= matrix_size: #col
                element = element - matrix_size
                zeros = [t for t in zeros if t[1] != element]
            else: #row
                zeros = [t for t in zeros if t[0] != element]
        return len(zeros) == 0

    def get_minimal_lines(self, zeros, matrix_size):
        indices = list(range(2*matrix_size))  # rows + cols
        combs = []
        for i in range(1, matrix_size+1):
            flag=False
            for comb in itertools.combinations(indices, i):
                if self.check_coverage(comb, zeros, matrix_size):
                    flag = True
                    combs.append(comb)
            if flag:
                break
        return combs, i
    
    def uncovered_indices(self, comb, matrix_size):
        rows_cov = {i for i in comb if i < matrix_size}
        cols_cov = {i - matrix_size for i in comb if i >= matrix_size}

        return [
            (r, c)
            for r in range(matrix_size)
            for c in range(matrix_size)
            if r not in rows_cov and c not in cols_cov
        ]

    def uncovered_rows(self, comb, matrix_size):
        covered_rows = {i for i in comb if i < matrix_size}
        return [
            (r, c)
            for r in range(matrix_size)
            for c in range(matrix_size)
            if r not in covered_rows
        ]

    def covered_cols(self, comb, matrix_size):
        covered = {i - matrix_size for i in comb if i >= matrix_size} 
        return [(r, c) for c in covered for r in range(matrix_size)]
    
    def all_zero_assignments(self, matrix, matrix_size):
        Z = (matrix == 0)
        return [
            tuple((r, p[r]) for r in range(matrix_size)) 
            for p in itertools.permutations(range(matrix_size)) 
            if np.all(Z[range(matrix_size), p])
        ]
        
    def step_one(self, matrix_size, numbers): #row reduction
        mat = np.array(numbers).reshape(matrix_size, matrix_size)
        return mat - mat.min(axis=1, keepdims=True)
    
    def step_two(self, matrix): #column reduction
        mat = np.array(matrix)
        return mat - mat.min(axis=0, keepdims=True)

    def step_three(self, matrix, matrix_size): #cover zeros
        zeros = list(map(tuple, np.argwhere(matrix == 0)))
        combs, i = self.get_minimal_lines(zeros, matrix_size)
        return combs, i
    
    def step_four(self, comb, matrix, matrix_size): #adjust matrix
        uncov = self.uncovered_indices(comb, matrix_size)
        min_val = min(matrix[r, c] for r, c in uncov)

        uncovered_rows = self.uncovered_rows(comb, matrix_size)
        matrix[tuple(zip(*uncovered_rows))] -= min_val

        covered_cols = self.covered_cols(comb, matrix_size)
        matrix[tuple(zip(*covered_cols))] += min_val
        return matrix

    def step_five(self, matrix, matrix_size):
        zero_assignments = self.all_zero_assignments(matrix, matrix_size)
        return zero_assignments
    
    def loop(self, matrix, matrix_size, count):
        combs, i = self.step_three(matrix, matrix_size)
        self.path.append(('Step3', (combs, i, count)))
        if i == matrix_size:
            return [(matrix.copy(), count)]

        leaves = []
        for comb in combs:
            branched = self.step_four(comb, matrix.copy(), matrix_size)
            self.path.append(('Step4', (branched, comb, count)))
            leaves.extend(self.loop(branched, matrix_size, count + 1))
        return leaves
    
    def hungarian_method(self, numbers, matrix_size):
        matrix = self.step_one(matrix_size, numbers)
        self.path.append(('Step1', matrix))
        matrix = self.step_two(matrix)
        self.path.append(('Step2', matrix))
        leaves = self.loop(matrix, matrix_size, 0)  # list of (matrix, count)

        all_assignments = []
        per_assignment_loops = []

        for m, c in leaves:
            assignments = self.step_five(m, matrix_size)
            self.path.append(('Step5', (m, c, assignments)))
            all_assignments.extend(assignments)
            per_assignment_loops.extend([c] * len(assignments))

        dedup, seen = [], set()
        for match in all_assignments:
            key = tuple(sorted(match))  # canonicalize a matching like [(r,c), ...]
            if key not in seen:
                seen.add(key)
                dedup.append(match)

        stats = {
            "num_paths": len(leaves),                       
            "assignments_found": len(dedup),                  
            "max_depth": max((c for _, c in leaves), default=0),
            "total_loops": sum(c for _, c in leaves)
        }

        return dedup, stats
    
    def _run_addition(self):
        sumx = self.a+self.b
        self.addition_data.append({"sumx": sumx})

    def generate(self):
        base = {}

        view0 = [
            {
                "type": "Text",
                "content": f"Gegeben ist die folgende Distanzmatrix zweier Schemata, in der jeder Eintrag die Distanz zwischen einem Attribut aus Schema A ({', '.join(self.schemaA)}) und einem Attribut aus Schema B ({', '.join(self.schemaB)}) beschreibt:",    
            },
            {
                "type": "MatrixInput",
                "id": "start-matrix",
                "title": "Distanzmatrix",
                "rows": [[a] for a in self.schemaA],
                "cols": [[b] for b in self.schemaB],
                "values": [self.numbers[i:i+self.matrix_size] for i in range(0, len(self.numbers), self.matrix_size)]
            },
            {
                "type": "Text",
                "content": f"Führen Sie den ersten Schritt der ungarischen Methode aus, indem Sie in jeder Zeile das kleinste Element bestimmen und dieses Minimum von allen Elementen der jeweiligen Zeile subtrahieren.",    
            },
            {
                "type": "Text",
                "content": f"{self.path}, {self.path[0]}, {self.path[0][1]}, {self.path[0][1][0,1]}",    
            }
        ]

        base["lastView"] = [
            {
                "type": "Text",
                "content": ""    
            }
        ]

        base["view1"] = view0
        return base

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------
    def evaluate(self, user_input):
        results = {}
        step1 = self.path[0][1]
        for row in range(self.matrix_size):
            for col in range(self.matrix_size):
                results[f'start-matrix:cell:{row},{col}'] = {
                    "correct": float(user_input.get(f'start-matrix:cell:{row},{col}')) == float(step1[row,col]),
                    "expected": float(step1[row,col])
                }
        print(results)
        return results

