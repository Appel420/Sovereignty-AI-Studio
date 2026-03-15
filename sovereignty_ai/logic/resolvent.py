"""Resolution-based First-Order Logic prover - proves when you lie."""

from typing import List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class LogicOperator(Enum):
    """Logical operators."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    IMPLIES = "IMPLIES"
    IFF = "IFF"


@dataclass
class Clause:
    """A clause in First-Order Logic."""
    literals: Set[str]
    is_positive: bool = True
    
    def __hash__(self):
        return hash(frozenset(self.literals))
    
    def __eq__(self, other):
        return self.literals == other.literals and self.is_positive == other.is_positive
    
    def __repr__(self):
        prefix = "" if self.is_positive else "¬"
        return f"{prefix}({' ∨ '.join(sorted(self.literals))})"


class ResolutionProver:
    """
    Resolution-based theorem prover for First-Order Logic.
    Detects contradictions and inconsistencies - proves when statements are lies.
    """
    
    def __init__(self):
        """Initialize the resolution prover."""
        self.knowledge_base: Set[Clause] = set()
        self.contradiction_found = False
        self.proof_steps: List[str] = []
    
    def add_clause(self, literals: List[str], is_positive: bool = True):
        """
        Add a clause to the knowledge base.
        
        Args:
            literals: List of literal strings
            is_positive: Whether the clause is positive (True) or negated (False)
        """
        clause = Clause(set(literals), is_positive)
        self.knowledge_base.add(clause)
    
    def add_statement(self, statement: str, is_true: bool = True):
        """
        Add a logical statement to the knowledge base.
        
        Args:
            statement: Statement string
            is_true: Whether the statement is asserted as true or false
        """
        self.add_clause([statement], is_positive=is_true)
    
    def negate_clause(self, clause: Clause) -> Clause:
        """
        Negate a clause.
        
        Args:
            clause: Input clause
            
        Returns:
            Negated clause
        """
        return Clause(clause.literals, not clause.is_positive)
    
    def resolve(self, clause1: Clause, clause2: Clause) -> Optional[Clause]:
        """
        Apply resolution rule to two clauses.
        
        Args:
            clause1: First clause
            clause2: Second clause
            
        Returns:
            Resolvent clause if resolution is possible, None otherwise
        """
        # Find complementary literals
        for lit in clause1.literals:
            # Check if negation exists in clause2
            if lit in clause2.literals and clause1.is_positive != clause2.is_positive:
                # Create resolvent
                new_literals = (clause1.literals | clause2.literals) - {lit}
                
                if len(new_literals) == 0:
                    # Empty clause - contradiction found
                    self.contradiction_found = True
                    return Clause(set(), True)
                
                # Determine polarity of resolvent
                is_positive = len(clause1.literals) == 1 or len(clause2.literals) == 1
                
                return Clause(new_literals, is_positive)
        
        return None
    
    def prove_by_contradiction(self, query: str) -> bool:
        """
        Prove a query by contradiction (refutation).
        
        Args:
            query: Query to prove
            
        Returns:
            True if query is provable, False otherwise
        """
        # Add negation of query to KB
        negated_query = Clause({query}, False)
        working_set = self.knowledge_base.copy()
        working_set.add(negated_query)
        
        self.proof_steps = [f"Proving: {query}"]
        self.proof_steps.append(f"Added ¬{query} to KB")
        
        new_clauses = set()
        iteration = 0
        max_iterations = 100
        
        while iteration < max_iterations:
            iteration += 1
            clause_list = list(working_set)
            
            # Try to resolve all pairs
            for i, clause1 in enumerate(clause_list):
                for clause2 in clause_list[i+1:]:
                    resolvent = self.resolve(clause1, clause2)
                    
                    if resolvent is not None:
                        self.proof_steps.append(
                            f"Step {iteration}: Resolved {clause1} and {clause2} → {resolvent}"
                        )
                        
                        if self.contradiction_found:
                            self.proof_steps.append("⚠️ CONTRADICTION FOUND - Statement is a LIE")
                            return True
                        
                        if resolvent not in working_set:
                            new_clauses.add(resolvent)
            
            # Add new clauses to working set
            if not new_clauses:
                # No new clauses, proof failed
                self.proof_steps.append("No contradiction found - Cannot prove")
                return False
            
            working_set.update(new_clauses)
            new_clauses.clear()
        
        self.proof_steps.append("Maximum iterations reached")
        return False
    
    def detect_lie(self, statement: str, context: List[Tuple[str, bool]]) -> bool:
        """
        Detect if a statement is a lie given contextual facts.
        
        Args:
            statement: Statement to check
            context: List of (fact, is_true) tuples providing context
            
        Returns:
            True if statement is provably false (a lie), False otherwise
        """
        # Clear knowledge base
        self.knowledge_base.clear()
        self.contradiction_found = False
        self.proof_steps.clear()
        
        # Add context to KB
        for fact, is_true in context:
            self.add_statement(fact, is_true)
        
        # Try to prove the statement
        # If we can prove its negation, it's a lie
        result = self.prove_by_contradiction(statement)
        
        return result
    
    def get_proof_trace(self) -> str:
        """
        Get the proof trace as a formatted string.
        
        Returns:
            Formatted proof steps
        """
        return "\n".join(self.proof_steps)
    
    def check_consistency(self) -> bool:
        """
        Check if the knowledge base is consistent.
        
        Returns:
            True if consistent, False if contradictory
        """
        working_set = self.knowledge_base.copy()
        
        for i, clause1 in enumerate(list(working_set)):
            for clause2 in list(working_set)[i+1:]:
                resolvent = self.resolve(clause1, clause2)
                
                if resolvent is not None and self.contradiction_found:
                    return False
        
        return True
