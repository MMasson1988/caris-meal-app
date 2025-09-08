USE caris_db;
SELECT 
    ld.name AS departement,
    lc.name AS commune,
    ls.name AS section,
    c.name AS club_name,
    lh.name AS hospital,
    p.patient_code,
    tmi.first_name,
    tmi.last_name,
    tmi.dob,
    MIN(cs.date) AS first_session_date,
    MAX(cs.date) AS last_session_date,
    TIMESTAMPDIFF(DAY, MAX(cs.date), NOW()) AS days_from_last_session,
    IF(TIMESTAMPDIFF(DAY,
            '2024-06-17',
            MAX(cs.date)) > 0,
        'yes',
        'no') AS has_session_siy
FROM
    session s
        INNER JOIN
    tracking_motherbasicinfo tmi ON tmi.id_patient = s.id_patient
        INNER JOIN
    patient p ON p.id = s.id_patient
        INNER JOIN
    club_session cs ON cs.id = s.id_club_session
        INNER JOIN
    club c ON c.id = cs.id_club
        INNER JOIN
    lookup_club_type lct ON lct.id = c.club_type
        INNER JOIN
    lookup_hospital lh ON lh.id = c.id_hospital
        LEFT JOIN
    lookup_section ls ON ls.id = lh.section
        LEFT JOIN
    lookup_commune lc ON lc.id = lh.commune
        LEFT JOIN
    lookup_departement ld ON ld.id = lc.departement
WHERE
    s.is_present = 1 AND c.club_type = 1
GROUP BY s.id_patient