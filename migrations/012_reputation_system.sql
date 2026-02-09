-- Migration 012: Reputation System
-- 1. Create reputation_criteria table
CREATE TABLE reputation_criteria (
    id INTEGER PRIMARY KEY,
    code_key TEXT NOT NULL,      -- i18n key like 'arrived_on_time'
    role_client BOOLEAN NOT NULL, -- TRUE for feedback TO master, FALSE for feedback TO client
    group_key TEXT               -- for mutual exclusion like 'arrival', 'behavior'
);

-- 2. Create reputation_votes table
CREATE TABLE reputation_votes (
    id INTEGER PRIMARY KEY,
    from_client BOOLEAN NOT NULL, -- FALSE if it's master rating client
    order_id INTEGER NOT NULL REFERENCES orders(id),
    criterion_id INTEGER NOT NULL REFERENCES reputation_criteria(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Insert criteria for Client -> Master (role_client = 1)
-- Group: arrival
INSERT INTO reputation_criteria (id,code_key,role_client,group_key) VALUES
	 (1,'crit_m_on_time',1,'rep_group_arrival'),
	 (2,'crit_m_late',1,'rep_group_arrival'),
	 (3,'crit_m_no_show',1,'rep_group_arrival'),
	 (4,'crit_m_polite',1,'rep_group_communication'),
	 (5,'crit_m_tense',1,'rep_group_communication'),
	 (6,'crit_m_rude',1,'rep_group_communication'),
	 (7,'crit_m_good',1,'rep_group_result'),
	 (8,'crit_m_minor_issues',1,'rep_group_result'),
	 (9,'crit_m_redo',1,'rep_group_result'),
	 (10,'crit_m_as_agreed',1,'rep_group_agreements');
INSERT INTO reputation_criteria (id,code_key,role_client,group_key) VALUES
	 (11,'crit_m_changed_on_spot',1,'rep_group_agreements'),
	 (12,'crit_m_price_jump',1,'rep_group_agreements'),
	 (13,'crit_c_on_time',0,'rep_group_punctuality'),
	 (14,'crit_c_late',0,'rep_group_punctuality'),
	 (15,'crit_c_no_show',0,'rep_group_punctuality'),
	 (16,'crit_c_polite',0,'rep_group_communication'),
	 (17,'crit_c_difficult',0,'rep_group_communication'),
	 (18,'crit_c_conflict',0,'rep_group_communication'),
	 (19,'crit_c_match_desc',0,'rep_group_agreements'),
	 (20,'crit_c_changed_details',0,'rep_group_agreements');
INSERT INTO reputation_criteria (id,code_key,role_client,group_key) VALUES
	 (21,'crit_c_changed_reqs',0,'rep_group_agreements'),
	 (22,'crit_c_paid_ok',0,'rep_group_payment'),
	 (23,'crit_c_paid_late',0,'rep_group_payment'),
	 (24,'crit_c_payment_dispute',0,'rep_group_payment');
