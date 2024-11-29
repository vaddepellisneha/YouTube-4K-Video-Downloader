// Include WordPress to use its functions
require_once( $_SERVER['DOCUMENT_ROOT'] . '/wp-load.php' );

// Register a REST route in WordPress
add_action('rest_api_init', function() {
    register_rest_route('my_namespace/v1', '/my_route', array(
        'methods' => 'GET',
        'callback' => 'my_callback_function',
    ));
});
