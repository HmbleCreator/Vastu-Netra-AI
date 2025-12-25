┌─────────────────────────────────────────────────────────────────────────────┐
│                           VGF-SA SOLVER WORKFLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

  USER INPUT                          VASTU MAPS                    
      │                                   │                         
      ▼                                   ▼                         
┌──────────────┐                  ┌───────────────────┐            
│ Plot Size    │                  │ NE → Pooja/Living │            
│ BHK Config   │──────────────────│ SE → Kitchen      │            
│ Orientation  │                  │ SW → Master Bed   │            
└──────────────┘                  │ NW → Bathroom     │            
      │                           └───────────────────┘            
      │                                   │                         
      └─────────────┬─────────────────────┘                         
                    ▼                                               
         ┌──────────────────────┐                                   
         │   CONSTRAINT GRAPH   │                                   
         │  ├─ Adjacency Rules  │                                   
         │  ├─ No Overlaps      │                                   
         │  ├─ Stay in Bounds   │                                   
         │  └─ Aspect Ratios    │                                   
         └──────────────────────┘                                   
                    │                                               
                    ▼                                               
         ┌──────────────────────┐                                   
         │ SIMULATED ANNEALING  │◄─────────────┐                    
         │  1. Random Start     │              │                    
         │  2. Calculate Score  │              │ Repeat until       
         │  3. Perturb Rooms    │              │ converged          
         │  4. Accept/Reject    │──────────────┘                    
         │  5. Cool Down        │                                   
         └──────────────────────┘                                   
                    │                                               
                    ▼                                               
         ┌──────────────────────┐                                   
         │   SCORING FUNCTION   │                                   
         │  Vastu Score (94%)   │                                   
         │  - Overlap Penalty   │                                   
         │  - Boundary Penalty  │                                   
         └──────────────────────┘                                   
                    │                                               
                    ▼                                               
         ┌──────────────────────┐                                   
         │       OUTPUT         │                                   
         │  Optimized Layout    │                                   
         │  Room Positions      │                                   
         │  Vastu Compliance    │                                   
         └──────────────────────┘                                   