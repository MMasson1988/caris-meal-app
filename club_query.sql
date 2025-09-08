SELECT
    IF(p.linked_to_id_patient > 0, p.linked_to_id_patient, p.id) AS id_patient,
    lh.name AS hopital,
    CONCAT(lh.city_code, '/', lh.hospital_code) AS site_code,
    c.name AS club_name,
    lct.name AS club_type,
    p.patient_code,
    cs.date AS session_date,
    lctc.name_fr AS topic,
    a.date AS first_attendance_date,
    b.date AS last_attendance_date,
    aa.date as first_attendance_date_by_club,
    COALESCE(ti.first_name, tm.first_name) AS first_name,
    COALESCE(ti.last_name, tm.last_name) AS last_name,
    COALESCE(ti.dob, tm.dob) AS dob,
    COALESCE(ti.is_abandoned, tm.is_abandoned) as is_abandoned,
    COALESCE(ti.is_dead, tm.is_dead) as is_dead,
    IF(tm.is_graduate=1, 'Yes', 'Non') as graduation,
    tm.graduation_date,
    IF(ti.gender=1, 'male', IF(ti.gender=2, 'female', IF(ti.gender=3, 'unknown', ti.gender))) as sex,
    ss.clore,
    ss.nbre_deparasitaires,
    ss.nbre_preservatifs,
    ss.nbre_vit_a,
    ss.nbre_moustiquaires,
    ss.code,
    ss.is_patient_tb,
    ss.is_patient_on_pf,
    ss.adh,
    ss.is_present as present,
    lca.name as raison_absence
FROM
    session ss
LEFT JOIN club_session cs ON cs.id = ss.id_club_session
LEFT JOIN club c ON c.id = cs.id_club
LEFT JOIN lookup_club_type lct ON lct.id = c.club_type
LEFT JOIN lookup_club_topic lctc ON lctc.id = cs.topic
LEFT JOIN patient p ON p.id = ss.id_patient
LEFT JOIN tracking_motherbasicinfo tm ON tm.id_patient = IF(p.linked_to_id_patient > 0, p.linked_to_id_patient, ss.id_patient)
LEFT JOIN tracking_infant ti ON ti.id_patient = IF(p.linked_to_id_patient > 0, p.linked_to_id_patient, ss.id_patient)
LEFT JOIN lookup_hospital lh ON lh.id = c.id_hospital
LEFT JOIN (
    SELECT MIN(cs1.date) AS date, s1.id_patient, pp.main_id
    FROM session s1
    LEFT JOIN club_session cs1 ON cs1.id = s1.id_club_session
    LEFT JOIN (
        SELECT p12.*, IF(p12.linked_to_id_patient > 0, p12.linked_to_id_patient, p12.id) AS main_id
        FROM patient p12
    ) pp ON pp.id = s1.id_patient
    WHERE s1.is_present IS NOT NULL
    GROUP BY pp.main_id
) a ON a.main_id = IF(p.linked_to_id_patient > 0, p.linked_to_id_patient, p.id)
LEFT JOIN (
    SELECT MAX(cs2.date) AS date, s2.id_patient
    FROM session s2
    LEFT JOIN club_session cs2 ON cs2.id = s2.id_club_session
    WHERE s2.is_present IS NOT NULL
    GROUP BY s2.id_patient
) b ON b.id_patient = ss.id_patient
LEFT JOIN (
    SELECT MIN(cs3.date) AS date, s3.id_patient, cs3.id_club
    FROM session s3
    LEFT JOIN club_session cs3 ON cs3.id = s3.id_club_session
    WHERE s3.is_present IS NOT NULL
    GROUP BY cs3.id_club, s3.id_patient
) aa ON aa.id_patient = ss.id_patient AND c.id = aa.id_club
LEFT JOIN lookup_club_attendance lca ON lca.id = ss.is_present
WHERE
    ss.is_present IS NOT NULL
    AND p.id IS NOT NULL
    AND cs.date BETWEEN :start_date AND :end_date
ORDER BY CONCAT(lh.city_code, '/', lh.hospital_code), c.name, p.patient_code, cs.date
LIMIT 100000000
