/*jshint esversion: 6 */
/**
 * Wrapper around ReconnectingWebSocket
 */

import ReconnectingWebSocket from "reconnecting-websocket";

export class GUSocket {
  constructor(settings) {
    this.endpoint = settings.endpoint;
    this.tolerance =
      settings.lagTolerance === undefined ? 0.1 : settings.lagTolerance;
    this.experimentBroadcastChannel = settings.broadcast;
    this.experimentControlChannel = settings.control;
    this.callbackMap = settings.callbackMap;
    this.experimentSocket = this._makeSocket(
      this.endpoint,
      this.experimentBroadcastChannel,
      this.tolerance,
    );

    this.experimentSocket.onmessage = (event) => {
      this._experimentDispatch(event);
    };
  }

  addGameChannels(broadcastChannel, controlChannel) {
    this.broadcastChannel = broadcastChannel;
    this.controlChannel = controlChannel;
    this.gameSocket = this._makeSocket(
      this.endpoint,
      this.broadcastChannel,
      this.tolerance,
    );

    this.gameSocket.onmessage = (event) => {
      this._dispatch(event);
    };
    this.openGame();
  }

  openExperiment() {
    const isOpen = $.Deferred();
    this.experimentSocket.onopen = () => {
      isOpen.resolve();
    };

    return isOpen;
  }

  openGame() {
    const isOpen = $.Deferred();
    this.gameSocket.onopen = () => {
      isOpen.resolve();
    };

    return isOpen;
  }

  sendToExperiment(data) {
    const msg = JSON.stringify(data);
    const channel = this.experimentControlChannel;
    console.log(`Sending message to the ${channel} channel: ${msg}`);
    this.experimentSocket.send(`${channel}:${msg}`);
  }

  send(data) {
    const msg = JSON.stringify(data);
    const channel = this.controlChannel;
    console.log(`Sending message to the ${channel} channel: ${msg}`);
    this.gameSocket.send(`${channel}:${msg}`);
  }

  broadcast(data) {
    const msg = JSON.stringify(data);
    const channel = this.broadcastChannel;
    console.log(`Broadcasting message to the ${channel} channel: ${msg}`);
    this.gameSocket.send(`${channel}:${msg}`);
  }

  _makeSocket(endpoint, channel, tolerance) {
    const ws_scheme =
      window.location.protocol === "https:" ? "wss://" : "ws://";
    const app_root = `${ws_scheme}${location.host}/`;
    const socketUrl = `${app_root}${endpoint}?channel=${channel}&tolerance=${tolerance}`;
    const socket = new ReconnectingWebSocket(socketUrl);
    socket.debug = true;

    return socket;
  }

  _baseDispatch(event, marker) {
    const msg = JSON.parse(event.data.substring(marker.length));
    const callback = this.callbackMap[msg.type];
    if (callback !== undefined) {
      callback(msg, this);
    } else {
      console.log(`Unrecognized message type ${msg.type} from backend.`);
    }
  }

  _experimentDispatch(event) {
    const marker = `${this.experimentBroadcastChannel}:`;
    if (!event.data.startsWith(marker)) {
      console.log(
        `Message was not on channel ${this.experimentBroadcastChannel}. Ignoring.`,
      );
      return;
    }
    this._baseDispatch(event, marker);
  }

  _dispatch(event) {
    const marker = `${this.broadcastChannel}:`;
    if (!event.data.startsWith(marker)) {
      console.log(
        `Message was not on channel ${this.broadcastChannel}. Ignoring.`,
      );
      return;
    }
    this._baseDispatch(event, marker);
  }
}
