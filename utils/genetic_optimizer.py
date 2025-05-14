import random
import numpy as np
from deap import base, creator, tools, algorithms

class GeneticOptimizer:
    """
    A genetic algorithm optimizer for study routines.
    The optimizer generates an optimal study routine for the evening (6 PM - 12 AM)
    based on course weights and study constraints.
    """
    
    def __init__(self, courses, dinner_hour=8, days=None):
        """
        Initialize the genetic optimizer with courses and constraints.
        
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
        
        # Maximum number of consecutive same-course slots allowed
        self.max_consecutive_slots = 5
    
    def _setup_deap(self):
        """Set up the DEAP evolutionary algorithm components."""
        # Clean up any previous creation if they exist
        if 'FitnessMax' in creator.__dict__:
            del creator.FitnessMax
        if 'Individual' in creator.__dict__:
            del creator.Individual
            
        # Create fitness and individual classes
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
        
        # Initialize toolbox
        self.toolbox = base.Toolbox()
        
        # Register gene (allele) and individual creation
        self.toolbox.register("attr_course", self._random_course)
        self.toolbox.register("individual", tools.initRepeat, creator.Individual, 
                             self.toolbox.attr_course, n=self.num_slots)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        # Register genetic operators
        self.toolbox.register("evaluate", self._evaluate_fitness)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", self._mutate, indpb=0.2)
        self.toolbox.register("select", tools.selTournament, tournsize=3)
    
    def _random_course(self):
        """Generate a random course from available courses."""
        # -1 means no course assigned to the slot
        if not self.courses:
            return -1
        else:
            return random.randint(0, self.num_courses - 1)
    
    def _mutate(self, individual, indpb):
        """Custom mutation operator that randomly changes course assignments."""
        for i in range(len(individual)):
            if random.random() < indpb:
                individual[i] = self._random_course()
        return individual,
    
    def _evaluate_fitness(self, individual):
        """
        Evaluate the fitness of a study routine.
        
        The fitness is based on:
        1. Total weight of courses included in the routine
        2. Penalties for consecutive same-course slots
        
        Returns:
            Tuple containing the fitness score
        """
        # Get the latest course weights directly from the course objects
        course_weights = {course.course_code: course.current_weight for course in self.courses}
        
        # Convert individual indices to course codes
        routine = {}
        for i, course_idx in enumerate(individual):
            # -1 means no course
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
        
        return (fitness,)
    
    def optimize(self, population_size=50, generations=40):
        """
        Run the genetic algorithm optimization.
        
        Args:
            population_size: Size of the population
            generations: Number of generations to evolve
            
        Returns:
            Tuple containing:
            - Dictionary mapping slot keys to course codes for the optimized routine
            - Final fitness score
        """
        # Update course weights before optimization
        self.course_weights = {course.course_code: course.current_weight for course in self.courses}
        
        # Set up DEAP components every time to ensure fresh state
        self._setup_deap()
        
        # Create initial population
        pop = self.toolbox.population(n=population_size)
        
        # Keep track of the best individual
        hof = tools.HallOfFame(1)
        
        # Track statistics
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("min", np.min)
        stats.register("max", np.max)
        
        # Run the algorithm
        algorithms.eaSimple(pop, self.toolbox, cxpb=0.7, mutpb=0.2, 
                           ngen=generations, stats=stats, halloffame=hof, verbose=False)
        
        # Get the best solution
        best_individual = hof[0]
        
        # Convert to a usable routine
        optimized_routine = {}
        for i, course_idx in enumerate(best_individual):
            if course_idx >= 0 and course_idx < self.num_courses:
                slot_key = self.slots[i]
                optimized_routine[slot_key] = self.course_codes[course_idx]
        
        # Get the fitness score
        fitness_score = best_individual.fitness.values[0]
        
        return optimized_routine, fitness_score 