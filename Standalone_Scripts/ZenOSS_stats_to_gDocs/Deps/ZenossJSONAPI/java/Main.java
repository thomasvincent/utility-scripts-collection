/* Zenoss-4.x JSON API Example (java)
 *
 * This main function trivially exercises the JsonApi class that connects to
 * the Zenoss-4 JSON API.
 *
 */

package zenoss_api;

public class Main {

    public static void main(String[] args) throws Exception {
        JsonApi ja = new JsonApi();
        System.out.println("all devices: " + ja.getDevices());
        System.out.println("all events: " + ja.getEvents());
        ja.close();
    }

}
