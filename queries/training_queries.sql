-- queries/training_queries.sql

-- Create new training record
CREATE OR REPLACE FUNCTION insert_training_record(
    p_userid INT,
    p_courseid VARCHAR,
    p_completion_date DATE
) RETURNS INT AS $$
DECLARE
    new_id INT;
BEGIN
    INSERT INTO training_status_data (userid, courseid, completion_date)
    VALUES (p_userid, p_courseid, p_completion_date)
    RETURNING id INTO new_id;
    
    -- Update training status and eligibility
    PERFORM update_training_status();
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- Update existing training record
CREATE OR REPLACE FUNCTION update_training_record(
    p_id INT,
    p_completion_date DATE
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE training_status_data
    SET completion_date = p_completion_date,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_id;
    
    -- Update training status and eligibility
    PERFORM update_training_status();
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Delete training record
CREATE OR REPLACE FUNCTION delete_training_record(p_id INT) RETURNS BOOLEAN AS $$
BEGIN
    DELETE FROM training_status_data
    WHERE id = p_id;
    
    -- Update training status and eligibility
    PERFORM update_training_status();
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Get users without specific training
CREATE OR REPLACE FUNCTION get_users_without_training(p_courseid VARCHAR) 
RETURNS TABLE (
    userid INT,
    first_name VARCHAR,
    last_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.userid,
        p.first_name,
        p.last_name
    FROM personal_data p
    WHERE NOT EXISTS (
        SELECT 1 
        FROM training_status_data t
        WHERE t.userid = p.userid
        AND t.courseid = p_courseid
    )
    ORDER BY p.last_name, p.first_name;
END;
$$ LANGUAGE plpgsql;