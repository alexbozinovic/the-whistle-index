export interface CrewRef {
  official_id: number;
  first_name: string;
  last_name: string;
  jersey_num: string | null;
}

export interface DifferentialPrimitives {
  home_minus_away_fouls_called: number;
  home_minus_away_free_throw_attempts: number;
  home_minus_away_fourth_quarter_fouls_called: number;
  home_minus_away_fourth_quarter_free_throw_attempts: number;
  home_minus_away_clutch_fouls_called: number;
  home_minus_away_clutch_free_throw_attempts: number;
}

export interface GameSummary {
  game_id: string;
  game_date_est: string;
  home_team_id: number;
  away_team_id: number;
  home_team_abbreviation: string;
  away_team_abbreviation: string;
  home_score: number;
  away_score: number;
  crew: CrewRef[];
  scores: {
    crew_impact_score: number;
    home_whistle_score: number;
    game_control_score: number;
    clutch_influence_score: number;
  };
  team_whistle_lean: {
    home_team_lean_points: number;
    away_team_lean_points: number;
    favored_team_id: number | null;
    favored_team_abbreviation: string;
  };
  differential_primitives: DifferentialPrimitives;
  main_drivers: string[];
}

export interface LeaderboardRow {
  referee_id: number;
  name: string;
  jersey_num: string | null;
  headshot_url: string | null;
  hometown: string | null;
  years_experience: number | null;
  nba_debut_year: number | null;
  games_worked: number;
  impact_score: number;
  home_whistle_score: number;
  game_control_score: number;
  clutch_influence_score: number;
  impact_volatility: number;
  avg_abs_team_lean: number;
  recent_trend_delta: number;
  favored_side_share: {
    home: number;
    away: number;
    even: number;
  };
}

export interface RefRecentGame {
  game_id: string;
  game_date_est: string;
  impact_score: number;
  home_whistle_score: number;
  game_control_score: number;
  clutch_influence_score: number;
  team_whistle_lean: {
    favored_team_abbreviation: string;
  };
  main_drivers: string[];
}

export interface RefProfile extends LeaderboardRow {
  recent_games: RefRecentGame[];
  impact_trend: Array<{
    game_id: string;
    game_date_est: string;
    impact_score: number;
  }>;
  favored_team_rank: Array<{
    team: string;
    count: number;
  }>;
}

export interface SnapshotData {
  generated_at_utc: string;
  games: GameSummary[];
  leaderboard: LeaderboardRow[];
  referees: RefProfile[];
  teams: TeamProfile[];
}

export interface TeamGame {
  game_id: string;
  game_date_est: string;
  is_home: boolean;
  team_score: number;
  opponent_score: number;
  team_lean_points: number;
  opponent_abbreviation: string;
  home_team_abbreviation: string;
  away_team_abbreviation: string;
}

export interface TeamProfile {
  team_abbreviation: string;
  games_played: number;
  avg_whistle_lean: number;
  home_avg_lean: number;
  away_avg_lean: number;
  home_games: number;
  away_games: number;
  most_favorable_refs: Array<{ referee_id: number; avg_lean: number }>;
  least_favorable_refs: Array<{ referee_id: number; avg_lean: number }>;
  recent_games: TeamGame[];
}
