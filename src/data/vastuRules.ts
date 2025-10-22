export interface VastuRule {
  id: string;
  category: string;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  applies_to: string[];
}

export const VASTU_RULES: VastuRule[] = [
  // Entrance & Main Door (Critical)
  {
    id: 'V001',
    category: 'Entrance',
    title: 'Main Entrance Direction',
    description: 'Main entrance should ideally be in North, East, or Northeast. North brings prosperity, East brings health, Northeast is most auspicious.',
    priority: 'critical',
    applies_to: ['entrance', 'main_door']
  },
  {
    id: 'V002',
    category: 'Entrance',
    title: 'Door Opening Direction',
    description: 'Main door should open inward in clockwise direction. It should open fully without obstruction.',
    priority: 'high',
    applies_to: ['entrance', 'main_door']
  },
  {
    id: 'V003',
    category: 'Entrance',
    title: 'Entrance Threshold',
    description: 'Entrance should have a raised threshold (6-9 inches) to prevent negative energy from entering.',
    priority: 'medium',
    applies_to: ['entrance']
  },

  // Kitchen Placement (Critical)
  {
    id: 'V004',
    category: 'Kitchen',
    title: 'Kitchen Location',
    description: 'Kitchen should be in Southeast (Agni corner) or Northwest. Southeast is most favorable as it aligns with fire element.',
    priority: 'critical',
    applies_to: ['kitchen']
  },
  {
    id: 'V005',
    category: 'Kitchen',
    title: 'Cooking Direction',
    description: 'Person cooking should face East while cooking. This ensures positive energy and health benefits.',
    priority: 'high',
    applies_to: ['kitchen', 'stove']
  },
  {
    id: 'V006',
    category: 'Kitchen',
    title: 'Kitchen Sink Position',
    description: 'Sink should be in Northeast corner of kitchen, away from stove. Water and fire elements should not be adjacent.',
    priority: 'high',
    applies_to: ['kitchen', 'sink']
  },
  {
    id: 'V007',
    category: 'Kitchen',
    title: 'Kitchen Door Alignment',
    description: 'Kitchen door should not directly face main entrance or bedroom door.',
    priority: 'medium',
    applies_to: ['kitchen']
  },

  // Bedroom Placement
  {
    id: 'V008',
    category: 'Bedroom',
    title: 'Master Bedroom Location',
    description: 'Master bedroom should be in Southwest direction. This brings stability and strengthens relationships.',
    priority: 'critical',
    applies_to: ['master_bedroom', 'bedroom']
  },
  {
    id: 'V009',
    category: 'Bedroom',
    title: 'Bed Placement Direction',
    description: 'Bed should be placed with head towards South or East. Avoid North direction as it may cause health issues.',
    priority: 'high',
    applies_to: ['bedroom', 'bed']
  },
  {
    id: 'V010',
    category: 'Bedroom',
    title: 'Children Bedroom',
    description: 'Children\'s bedroom should be in West or Northwest. This promotes growth and creativity.',
    priority: 'medium',
    applies_to: ['bedroom', 'children_room']
  },
  {
    id: 'V011',
    category: 'Bedroom',
    title: 'Guest Room Location',
    description: 'Guest room should be in Northwest corner. This ensures guests don\'t stay too long.',
    priority: 'low',
    applies_to: ['bedroom', 'guest_room']
  },

  // Bathroom & Toilet
  {
    id: 'V012',
    category: 'Bathroom',
    title: 'Bathroom Location',
    description: 'Bathrooms should be in Northwest, West, or South directions. Never in Northeast (most inauspicious).',
    priority: 'critical',
    applies_to: ['bathroom', 'toilet']
  },
  {
    id: 'V013',
    category: 'Bathroom',
    title: 'Toilet Seat Direction',
    description: 'Toilet seat should face North-South axis, never East-West. Person should face North or South while using.',
    priority: 'high',
    applies_to: ['toilet']
  },
  {
    id: 'V014',
    category: 'Bathroom',
    title: 'Attached Bathroom',
    description: 'Attached bathrooms in bedroom should be in West or Northwest corner of bedroom.',
    priority: 'medium',
    applies_to: ['bathroom']
  },

  // Living Room
  {
    id: 'V015',
    category: 'Living Room',
    title: 'Living Room Location',
    description: 'Living room should be in North, East, or Northeast. This promotes positive social interactions.',
    priority: 'high',
    applies_to: ['living_room', 'hall']
  },
  {
    id: 'V016',
    category: 'Living Room',
    title: 'Seating Arrangement',
    description: 'Heavy furniture should be placed in South and West walls. Owner should sit facing North or East.',
    priority: 'medium',
    applies_to: ['living_room']
  },
  {
    id: 'V017',
    category: 'Living Room',
    title: 'Living Room Height',
    description: 'Living room ceiling should be higher than other rooms to allow energy flow.',
    priority: 'low',
    applies_to: ['living_room']
  },

  // Pooja Room / Prayer Room
  {
    id: 'V018',
    category: 'Pooja Room',
    title: 'Pooja Room Location',
    description: 'Pooja room should be in Northeast corner (most auspicious). Alternatively, North or East.',
    priority: 'critical',
    applies_to: ['pooja_room', 'prayer_room']
  },
  {
    id: 'V019',
    category: 'Pooja Room',
    title: 'Idol Placement Direction',
    description: 'Idols should face East or West. Person praying should face East or North.',
    priority: 'high',
    applies_to: ['pooja_room']
  },
  {
    id: 'V020',
    category: 'Pooja Room',
    title: 'Pooja Room Restrictions',
    description: 'Pooja room should not be under staircase, adjacent to bathroom, or in basement.',
    priority: 'high',
    applies_to: ['pooja_room']
  },

  // Study Room / Home Office
  {
    id: 'V021',
    category: 'Study Room',
    title: 'Study Room Location',
    description: 'Study room should be in West, North, or Northeast. West direction enhances concentration.',
    priority: 'medium',
    applies_to: ['study_room', 'office']
  },
  {
    id: 'V022',
    category: 'Study Room',
    title: 'Study Desk Direction',
    description: 'Study desk should be placed so person faces East or North while studying/working.',
    priority: 'medium',
    applies_to: ['study_room', 'desk']
  },

  // Staircase
  {
    id: 'V023',
    category: 'Staircase',
    title: 'Staircase Location',
    description: 'Staircase should be in South, Southwest, or West. Never in Northeast (blocks positive energy).',
    priority: 'critical',
    applies_to: ['staircase', 'stairs']
  },
  {
    id: 'V024',
    category: 'Staircase',
    title: 'Staircase Direction',
    description: 'Stairs should turn clockwise while ascending. Number of steps should be odd.',
    priority: 'medium',
    applies_to: ['staircase']
  },
  {
    id: 'V025',
    category: 'Staircase',
    title: 'Space Under Stairs',
    description: 'Space under stairs should not be used for pooja room or kept empty. Can be used for storage.',
    priority: 'low',
    applies_to: ['staircase']
  },

  // Plot Shape & Orientation
  {
    id: 'V026',
    category: 'Plot',
    title: 'Plot Shape',
    description: 'Square or rectangular plots are most auspicious. Avoid irregular shapes, triangular, or T-shaped plots.',
    priority: 'high',
    applies_to: ['plot', 'land']
  },
  {
    id: 'V027',
    category: 'Plot',
    title: 'Plot Extensions',
    description: 'Extensions in Northeast bring prosperity. Extensions in Southwest should be avoided.',
    priority: 'medium',
    applies_to: ['plot']
  },
  {
    id: 'V028',
    category: 'Plot',
    title: 'Plot Slope',
    description: 'Plot should slope towards North or East. Water should flow towards Northeast.',
    priority: 'high',
    applies_to: ['plot', 'drainage']
  },

  // Balcony & Verandah
  {
    id: 'V029',
    category: 'Balcony',
    title: 'Balcony Location',
    description: 'Balconies should be in North, East, or Northeast. Avoid South or Southwest balconies.',
    priority: 'medium',
    applies_to: ['balcony', 'verandah']
  },
  {
    id: 'V030',
    category: 'Balcony',
    title: 'Balcony Size',
    description: 'Balconies in North and East can be larger. Keep Southwest balconies minimal or enclosed.',
    priority: 'low',
    applies_to: ['balcony']
  },

  // Windows & Ventilation
  {
    id: 'V031',
    category: 'Windows',
    title: 'Window Placement',
    description: 'More windows in North and East directions. This allows morning sunlight and positive energy.',
    priority: 'medium',
    applies_to: ['windows', 'ventilation']
  },
  {
    id: 'V032',
    category: 'Windows',
    title: 'Window Size',
    description: 'Windows should be larger in North and East, smaller in South and West.',
    priority: 'low',
    applies_to: ['windows']
  },

  // Water Features
  {
    id: 'V033',
    category: 'Water',
    title: 'Water Storage Location',
    description: 'Overhead water tanks should be in Southwest or West. Underground tanks in Northeast.',
    priority: 'high',
    applies_to: ['water_tank', 'storage']
  },
  {
    id: 'V034',
    category: 'Water',
    title: 'Bore Well Location',
    description: 'Bore well or water source should be in Northeast corner for prosperity.',
    priority: 'medium',
    applies_to: ['borewell', 'water_source']
  },

  // Dining Room
  {
    id: 'V035',
    category: 'Dining',
    title: 'Dining Room Location',
    description: 'Dining room should be in West or East. Can be attached to kitchen.',
    priority: 'medium',
    applies_to: ['dining_room']
  },
  {
    id: 'V036',
    category: 'Dining',
    title: 'Dining Table Direction',
    description: 'Family head should sit facing East or North while eating. Avoid facing South.',
    priority: 'low',
    applies_to: ['dining_table']
  },

  // Store Room & Utility
  {
    id: 'V037',
    category: 'Storage',
    title: 'Store Room Location',
    description: 'Store rooms should be in Southwest. Heavy items should be stored in South and West.',
    priority: 'low',
    applies_to: ['store_room', 'storage']
  },
  {
    id: 'V038',
    category: 'Storage',
    title: 'Safe/Locker Placement',
    description: 'Safes should be in North wall of room, opening towards North. Brings financial stability.',
    priority: 'medium',
    applies_to: ['safe', 'locker']
  },

  // General Structure
  {
    id: 'V039',
    category: 'Structure',
    title: 'Room Height',
    description: 'Southwest rooms should have lower ceiling than Northeast. Creates energy balance.',
    priority: 'low',
    applies_to: ['structure']
  },
  {
    id: 'V040',
    category: 'Structure',
    title: 'Central Space (Brahmasthan)',
    description: 'Center of house should be kept open and light. No pillars, heavy furniture, or toilets.',
    priority: 'critical',
    applies_to: ['structure', 'layout']
  },
  {
    id: 'V041',
    category: 'Structure',
    title: 'Load Distribution',
    description: 'Heavier construction should be in South and West. Keep North and East lighter.',
    priority: 'high',
    applies_to: ['structure', 'walls']
  },

  // Garage & Parking
  {
    id: 'V042',
    category: 'Garage',
    title: 'Garage Location',
    description: 'Garage should be in Northwest or Southeast. Avoid Northeast garage.',
    priority: 'medium',
    applies_to: ['garage', 'parking']
  },
  {
    id: 'V043',
    category: 'Garage',
    title: 'Vehicle Facing Direction',
    description: 'Vehicles should face East or North when parked.',
    priority: 'low',
    applies_to: ['garage', 'vehicle']
  },

  // Garden & Landscape
  {
    id: 'V044',
    category: 'Garden',
    title: 'Garden Location',
    description: 'Gardens should be in North, East, or Northeast. These directions promote growth.',
    priority: 'medium',
    applies_to: ['garden', 'landscape']
  },
  {
    id: 'V045',
    category: 'Garden',
    title: 'Tree Placement',
    description: 'Large trees should be in South or Southwest. Small plants in North and East. Avoid trees in Northeast.',
    priority: 'medium',
    applies_to: ['garden', 'trees', 'landscape']
  },
  {
    id: 'V046',
    category: 'Garden',
    title: 'Water Features in Garden',
    description: 'Fountains, ponds should be in Northeast. Promotes prosperity and positive energy flow.',
    priority: 'low',
    applies_to: ['garden', 'fountain', 'landscape']
  },

  // Colors & Elements
  {
    id: 'V047',
    category: 'Colors',
    title: 'Room Colors - Directional',
    description: 'Northeast: light blue/white; Southeast: orange/red; Southwest: brown/yellow; Northwest: white/gray.',
    priority: 'low',
    applies_to: ['colors', 'painting']
  },

  // Basement
  {
    id: 'V048',
    category: 'Basement',
    title: 'Basement Location',
    description: 'If basement needed, it should be in North or East. Avoid Southwest basement.',
    priority: 'medium',
    applies_to: ['basement']
  }
];

// Context engineering: Format rules for LLM consumption
export function getVastuContextPrompt(): string {
  return `# Vastu Shastra Rules Database

You are an expert Vastu consultant. Use these ${VASTU_RULES.length} rules to guide floor plan design:

## Critical Rules (MUST follow):
${VASTU_RULES.filter(r => r.priority === 'critical').map(r => 
  `- ${r.id}: ${r.title}: ${r.description}`
).join('\n')}

## High Priority Rules (Should follow):
${VASTU_RULES.filter(r => r.priority === 'high').map(r => 
  `- ${r.id}: ${r.title}: ${r.description}`
).join('\n')}

## Medium Priority Rules (Good to follow):
${VASTU_RULES.filter(r => r.priority === 'medium').map(r => 
  `- ${r.id}: ${r.title}: ${r.description}`
).join('\n')}

## Low Priority Rules (Optional):
${VASTU_RULES.filter(r => r.priority === 'low').map(r => 
  `- ${r.id}: ${r.title}: ${r.description}`
).join('\n')}

When designing floor plans:
1. ALWAYS prioritize Critical rules
2. Follow as many High priority rules as possible
3. Apply Medium and Low priority rules when they don't conflict with higher priorities
4. Explain which rules are being followed and why
5. If rules conflict with user requirements, explain the trade-offs
6. Consider the complete 8-directional mandala: N, NE, E, SE, S, SW, W, NW
`;
}

export function getVastuRulesByCategory(category: string): VastuRule[] {
  return VASTU_RULES.filter(rule => rule.category === category);
}

export function getVastuRulesByPriority(priority: VastuRule['priority']): VastuRule[] {
  return VASTU_RULES.filter(rule => rule.priority === priority);
}
