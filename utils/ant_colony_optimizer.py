import random
import numpy as np

class AntColonyOptimizer:
    """
    An Ant Colony Optimization (ACO) algorithm for study routines.
    The optimizer generates an optimal study routine for the evening (6 PM - 12 AM)
    based on course weights and study constraints.
    """
    
    def __init__(self, courses, dinner_hour=8, days=None):
        """
        Initialize the ACO optimizer with courses and constraints.
        
        Args:
            courses: List of course objects with course_code and current_weight attributes
            dinner_hour: Hour reserved for dinner (6-11, representing 6 PM to 11 PM)
            days: List of days to optimize for (defaults to all days of the week)
        """
        self.courses = courses
        self.course_codes = [course.course_code for course in courses]
        self.course_weights = {course.course_code: course.current_weight for course in courses}
        self.dinner_hour = dinner_hour
        self.days = days or ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
        
        # Each slot is identified by day_hour
        self.slots = []
        for day in self.days:
            for hour in range(6, 12):  # 6 PM to 11 PM
                if hour != dinner_hour:  # Skip dinner hour
                    self.slots.append(f"{day}_{hour}")
        
        # Number of slots available
        self.num_slots = len(self.slots)
        self.num_courses = len(self.courses)
        
        # Initialize pheromone matrix
        # Shape: num_slots x (num_courses + 1), where +1 is for "no course" option
        self.pheromones = np.ones((self.num_slots, self.num_courses + 1))
        
        # ACO parameters
        self.num_ants = 20
        self.evaporation_rate = 0.5
        self.alpha = 1.0  # pheromone influence
        self.beta = 2.0   # heuristic influence
        self.q0 = 0.9     # exploitation vs exploration
    
    def _heuristic_information(self):
        """
        Calculate heuristic information for each slot-course combination.
        
        Returns:
            Numpy array of shape (num_slots, num_courses + 1)
        """
        # Initialize with small values
        heuristic = np.ones((self.num_slots, self.num_courses + 1)) * 0.1
        
        # For each course, set the heuristic based on course weight
        for c_idx, course_code in enumerate(self.course_codes):
            weight = self.course_weights[course_code]
            
            # Higher weight = higher heuristic value
            for s_idx in range(self.num_slots):
                heuristic[s_idx, c_idx] = weight
                
            # No course option has lower preference
            heuristic[:, -1] = 0.1
        
        return heuristic
    
    def _evaluate_solution(self, solution):
        """
        Evaluate a solution's fitness.
        
        Args:
            solution: List of course indices for each slot (-1 for no course)
            
        Returns:
            Fitness score (higher is better)
        """
        # Get the latest course weights directly from the course objects
        course_weights = {course.course_code: course.current_weight for course in self.courses}
        
        # Convert solution indices to course codes
        routine = {}
        for i, course_idx in enumerate(solution):
            # Skip "no course" option (-1)
            if course_idx >= 0 and course_idx < self.num_courses:
                routine[self.slots[i]] = self.course_codes[course_idx]
        
        # Calculate total weight of included courses (without duplicates)
        included_courses = set(routine.values())
        total_weight = sum(course_weights.get(course, 0) for course in included_courses)
        
        # Apply penalties for consecutive same-course slots
        penalty = 0
        
        # Check consecutive slots per day
        for day in self.days:
            day_slots = [h for h in range(6, 12) if h != self.dinner_hour]
            day_slots.sort()  # Ensure slots are in order
            
            # Check for consecutive slots with the same course
            consecutive_count = 1
            prev_course = None
            
            for hour in day_slots:
                slot_key = f"{day}_{hour}"
                current_course = routine.get(slot_key)
                
                if current_course and current_course == prev_course:
                    consecutive_count += 1
                else:
                    # Apply penalty for the previous sequence if needed
                    if consecutive_count > 1:
                        if consecutive_count == 2:
                            penalty += 4
                        elif consecutive_count == 3:
                            penalty += 6
                        elif consecutive_count == 4:
                            penalty += 8
                        elif consecutive_count >= 5:
                            penalty += 10
                    consecutive_count = 1
                
                prev_course = current_course
            
            # Check final sequence
            if consecutive_count > 1:
                if consecutive_count == 2:
                    penalty += 4
                elif consecutive_count == 3:
                    penalty += 6
                elif consecutive_count == 4:
                    penalty += 8
                elif consecutive_count >= 5:
                    penalty += 10
        
        # Final fitness score (weight - penalties)
        fitness = total_weight - penalty
        
        return fitness, routine
    
    def _ant_tour(self, heuristic):
        """
        Generate a single ant's tour (solution).
        
        Args:
            heuristic: Heuristic information matrix
            
        Returns:
            List of course indices for each slot
        """
        solution = [-1] * self.num_slots  # Initialize with "no course" option
        
        # For each slot, select a course
        for slot_idx in range(self.num_slots):
            # Calculate probabilities for each course
            pheromone = self.pheromones[slot_idx, :]
            eta = heuristic[slot_idx, :]
            
            # Probability calculation: tau^alpha * eta^beta
            probabilities = (pheromone ** self.alpha) * (eta ** self.beta)
            probabilities = probabilities / np.sum(probabilities)
            
            # Exploitation vs exploration
            if random.random() < self.q0:
                # Exploitation: choose best course
                course_idx = np.argmax(probabilities)
            else:
                # Exploration: choose based on probability
                course_idx = random.choices(
                    range(self.num_courses + 1),
                    weights=probabilities,
                    k=1
                )[0]
            
            # Adjust to use -1 for the "no course" option
            if course_idx == self.num_courses:
                solution[slot_idx] = -1
            else:
                solution[slot_idx] = course_idx
        
        return solution
    
    def _update_pheromones(self, solutions, fitnesses):
        """
        Update pheromone trails based on ant solutions.
        
        Args:
            solutions: List of solutions (each is a list of course indices)
            fitnesses: List of fitness scores for each solution
        """
        # Evaporate all pheromones
        self.pheromones *= (1 - self.evaporation_rate)
        
        # Deposit new pheromones based on solution quality
        for solution, fitness in zip(solutions, fitnesses):
            # Normalize fitness (higher fitness = more pheromones)
            normalized_fitness = fitness / max(fitnesses) if max(fitnesses) > 0 else fitness
            
            # Update pheromones for each slot-course combination in this solution
            for slot_idx, course_idx in enumerate(solution):
                # Adjust course_idx for the "no course" option
                pheromone_idx = course_idx if course_idx >= 0 else self.num_courses
                
                # Deposit pheromones proportional to solution quality
                self.pheromones[slot_idx, pheromone_idx] += normalized_fitness
        
        # Ensure pheromones don't get too small
        self.pheromones = np.maximum(self.pheromones, 0.1)
    
    def optimize(self, iterations=30):
        """
        Run the ACO algorithm.
        
        Args:
            iterations: Number of iterations (generations) to run
            
        Returns:
            Tuple containing:
            - Dictionary mapping slot keys to course codes for the optimized routine
            - Final fitness score
        """
        # Update course weights before optimization
        self.course_weights = {course.course_code: course.current_weight for course in self.courses}
        
        # Calculate heuristic information
        heuristic = self._heuristic_information()
        
        # Keep track of the best solution
        best_solution = None
        best_fitness = -float('inf')
        best_routine = {}
        
        # Run for specified number of iterations
        for _ in range(iterations):
            # Generate solutions with multiple ants
            solutions = []
            for _ in range(self.num_ants):
                ant_solution = self._ant_tour(heuristic)
                solutions.append(ant_solution)
            
            # Evaluate all solutions
            evaluation_results = [self._evaluate_solution(solution) for solution in solutions]
            fitnesses = [result[0] for result in evaluation_results]
            routines = [result[1] for result in evaluation_results]
            
            # Find the best solution in this iteration
            best_idx = np.argmax(fitnesses)
            iteration_best_fitness = fitnesses[best_idx]
            iteration_best_solution = solutions[best_idx]
            iteration_best_routine = routines[best_idx]
            
            # Update global best if needed
            if iteration_best_fitness > best_fitness:
                best_fitness = iteration_best_fitness
                best_solution = iteration_best_solution
                best_routine = iteration_best_routine
            
            # Update pheromones
            self._update_pheromones(solutions, fitnesses)
        
        return best_routine, best_fitness 